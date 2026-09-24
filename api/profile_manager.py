"""Per-environment request leases and bounded configuration activation."""
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import threading
import time

from api.profiles import RuntimeProfile


class ProfileBusy(RuntimeError):
    pass


@dataclass(frozen=True)
class ProfileLease:
    profile: RuntimeProfile
    revision: str


class ProfileManager:
    def __init__(self, profiles, revisions, *, control_path=None):
        self._profiles = dict(profiles)
        self._revisions = dict(revisions)
        self.control_path = Path(control_path).absolute() if control_path else None
        self._condition = threading.Condition(threading.RLock())
        self._active = {key: 0 for key in profiles}
        self._changing = set()
        self._blocked = set()

    def snapshot(self, profile_id):
        with self._condition:
            return ProfileLease(self._profiles[profile_id], self._revisions[profile_id])

    def status(self, profile_id):
        with self._condition:
            return "BLOCKED" if profile_id in self._blocked else "CHANGING" if profile_id in self._changing else "AVAILABLE"

    @contextmanager
    def lease(self, profile_id):
        with self._condition:
            if profile_id in self._changing or profile_id in self._blocked:
                raise ProfileBusy("Environment is changing or requires recovery")
            pinned = ProfileLease(self._profiles[profile_id], self._revisions[profile_id])
            self._active[profile_id] += 1
        try:
            yield pinned
        finally:
            with self._condition:
                self._active[profile_id] -= 1
                self._condition.notify_all()

    @contextmanager
    def drain(self, profile_id, timeout=30.0):
        deadline = time.monotonic() + timeout
        with self._condition:
            if profile_id in self._changing or profile_id in self._blocked:
                raise ProfileBusy("Environment is already changing or requires recovery")
            self._changing.add(profile_id)
            while self._active[profile_id]:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._changing.remove(profile_id)
                    self._condition.notify_all()
                    raise ProfileBusy("Active requests did not finish before the change deadline")
                self._condition.wait(remaining)
        try:
            yield
        finally:
            with self._condition:
                self._changing.discard(profile_id)
                self._condition.notify_all()

    def publish(self, profile, revision):
        with self._condition:
            if profile.profile_id not in self._changing or self._active[profile.profile_id]:
                raise RuntimeError("Profile publication requires an exclusive drained environment")
            self._profiles[profile.profile_id] = profile
            self._revisions[profile.profile_id] = revision

    def block(self, profile_id):
        with self._condition:
            self._blocked.add(profile_id)


class SingleWorkerLease:
    """OS-owned lock: a process crash releases it without deleting stale files."""
    def __init__(self, control_path):
        self.path = Path(control_path).with_name("control.instance.lock")
        self.stream = None

    def __enter__(self):
        stream = self.path.open("a+b")
        if os.fstat(stream.fileno()).st_size == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            raise RuntimeError("The active control store requires a single API worker") from None
        self.stream = stream
        return self

    def __exit__(self, *_args):
        if self.stream:
            self.stream.close()
            self.stream = None
