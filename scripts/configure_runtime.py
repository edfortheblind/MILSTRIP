"""Administrator-only Tk screen; connection strings never enter the canvas app."""
from dataclasses import replace
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.profiles import (
    ConfigurationError, RuntimeConfig, RuntimeProfile, empty_runtime_config,
    load_runtime_config, runtime_config_path,
    target_summary, validate_runtime_config,
)
from scripts.runtime_host import require_legacy_editor, save_legacy_configuration


def test_profile(profile: RuntimeProfile) -> bool:
    """No schema creation, no request write and no raw driver error output."""
    from api.persistence import open_repository
    with open_repository(profile.provider, profile.connection_string) as repository:
        if not repository.health():
            return False
        repository.validate_identity(profile.profile_id)
    return True


class ConfigurationScreen:
    def __init__(self, window: tk.Tk, path: Path):
        require_legacy_editor()
        self.window, self.path = window, path
        self.config = load_runtime_config(path) if path.exists() else empty_runtime_config(path)
        self.saved_revision = self.config.revision if path.exists() else None
        self.selected = "stage"
        self.verified: set[tuple[str, str, str]] = set()
        self.profile = tk.StringVar(value="stage")
        self.provider = tk.StringVar()
        self.label = tk.StringVar()
        self.connection = tk.StringVar()
        self.enabled = tk.BooleanVar()
        self.summary = tk.StringVar()
        self.status = tk.StringVar(value="Changes take effect after the API is restarted.")
        self.results: queue.Queue = queue.Queue()
        self.testing = False
        window.title("MILSTRIP database configuration")
        window.minsize(740, 480)
        frame = ttk.Frame(window, padding=24)
        frame.grid(sticky="nsew")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Database configuration", font=("Segoe UI", 17, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))
        self._label(frame, "App environment", 1)
        choice = ttk.Combobox(frame, textvariable=self.profile, values=("stage", "prod"), state="readonly")
        choice.grid(row=1, column=1, sticky="ew", pady=5)
        choice.bind("<<ComboboxSelected>>", self.select_profile)
        self._label(frame, "Database provider", 2)
        ttk.Combobox(frame, textvariable=self.provider, values=("postgresql", "sqlserver"), state="readonly").grid(
            row=2, column=1, sticky="ew", pady=5)
        self._label(frame, "Display label", 3)
        ttk.Entry(frame, textvariable=self.label).grid(row=3, column=1, sticky="ew", pady=5)
        self._label(frame, "Current saved target", 4)
        ttk.Label(frame, textvariable=self.summary, wraplength=480).grid(row=4, column=1, sticky="w", pady=5)
        self._label(frame, "Replacement connection string", 5)
        ttk.Entry(frame, textvariable=self.connection, show="*").grid(row=5, column=1, sticky="ew", pady=5)
        ttk.Label(frame, text="Leave blank to keep the saved string. Stored values are never displayed.",
                  wraplength=480).grid(row=6, column=1, sticky="w", pady=(0, 8))
        ttk.Checkbutton(frame, text="Enable this environment", variable=self.enabled).grid(
            row=7, column=1, sticky="w", pady=5)
        ttk.Label(frame, text="Stage and Prod require separate databases and API credentials.",
                  wraplength=650).grid(row=8, column=0, columnspan=2, sticky="w", pady=(14, 8))
        self.test_button = ttk.Button(frame, text="Test connection", command=self.test_connection)
        self.test_button.grid(row=9, column=0, sticky="w", pady=12)
        self.save_button = ttk.Button(frame, text="Save pending configuration", command=self.save)
        self.save_button.grid(row=9, column=1, sticky="e", pady=12)
        ttk.Label(frame, textvariable=self.status, wraplength=660).grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(8, 0))
        window.protocol("WM_DELETE_WINDOW", self.close)
        self.show_profile()

    @staticmethod
    def _label(frame, text, row):
        ttk.Label(frame, text=text).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=5)

    @staticmethod
    def identity(profile):
        return profile.profile_id, profile.provider, profile.connection_string

    def show_profile(self):
        saved = self.config.profiles[self.selected]
        self.provider.set(saved.provider)
        self.label.set(saved.label)
        self.connection.set("")
        self.enabled.set(saved.enabled)
        self.summary.set(target_summary(saved))

    def candidate(self) -> RuntimeConfig:
        previous = self.config.profiles[self.selected]
        connection = self.connection.get() or previous.connection_string
        if self.provider.get() != previous.provider and not self.connection.get() and connection:
            raise ConfigurationError("Enter a replacement string when changing database provider.")
        profile = RuntimeProfile(self.selected, self.provider.get(), self.label.get().strip(),
                                 connection, self.enabled.get())
        profiles = dict(self.config.profiles)
        profiles[self.selected] = profile
        return validate_runtime_config(replace(self.config, profiles=profiles))

    def select_profile(self, _event=None):
        next_profile = self.profile.get()
        try:
            candidate = self.candidate()
        except ConfigurationError as error:
            self.profile.set(self.selected)
            self.status.set(str(error))
            return
        if candidate.profiles != self.config.profiles:
            self.profile.set(self.selected)
            self.status.set("Save the current changes before selecting another environment.")
            return
        self.selected = next_profile
        self.show_profile()

    def test_connection(self):
        try:
            require_legacy_editor()
            profile = self.candidate().profiles[self.selected]
            if not profile.connection_string:
                raise ConfigurationError("Enter a connection string before testing.")
        except ConfigurationError as error:
            self.status.set(str(error))
            return
        self.testing = True
        self.test_button.state(["disabled"])
        self.save_button.state(["disabled"])
        self.status.set("Checking database access, application schema and environment identity...")

        def run():
            try:
                success = test_profile(profile)
            except Exception:
                success = False
            self.results.put((profile, success))

        threading.Thread(target=run, daemon=True).start()
        self.window.after(100, self.finish_test)

    def finish_test(self):
        try:
            profile, success = self.results.get_nowait()
        except queue.Empty:
            self.window.after(100, self.finish_test)
            return
        self.testing = False
        self.test_button.state(["!disabled"])
        self.save_button.state(["!disabled"])
        if success:
            self.verified.add(self.identity(profile))
            self.status.set(f"{profile.profile_id.title()} connection and application identity verified. No data changed.")
        else:
            self.verified.discard(self.identity(profile))
            self.status.set("Connection test failed. Check the destination, credentials, certificate and provisioned environment identity.")

    def save(self):
        try:
            candidate = self.candidate()
            for key, profile in candidate.profiles.items():
                previous = self.config.profiles[key]
                if (profile.enabled and (not previous.enabled or self.identity(profile) != self.identity(previous))
                        and self.identity(profile) not in self.verified):
                    raise ConfigurationError("Test the new destination successfully before enabling and saving it.")
            self.config = save_legacy_configuration(candidate, self.path, expected_revision=self.saved_revision)
            self.saved_revision = self.config.revision
        except ConfigurationError as error:
            self.status.set(str(error))
            return
        self.show_profile()
        self.status.set("Saved. Restart the MILSTRIP API to activate this configuration, then verify each app's environment.")

    def close(self):
        try:
            changed = self.candidate().profiles != self.config.profiles
        except ConfigurationError:
            changed = True
        if changed and not messagebox.askyesno("Unsaved changes", "Discard the unsaved configuration changes?"):
            return
        self.window.destroy()


def main():
    try:
        require_legacy_editor()
    except ConfigurationError as error:
        print(str(error), file=sys.stderr)
        return 1
    window = tk.Tk()
    try:
        ConfigurationScreen(window, runtime_config_path())
    except ConfigurationError as error:
        window.withdraw()
        messagebox.showerror("MILSTRIP configuration", str(error))
        window.destroy()
        return 1
    window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
