"""Prompt privately; store a salted password verifier in the ignored .cred folder."""
import getpass
import json
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.auth import ITERATIONS, credential_path, password_digest


def main():
    path = credential_path()
    if not path.parent.is_dir():
        raise SystemExit("Run scripts/Set-LocalApiCredential.ps1 to prepare private storage first.")
    if path.exists() and input("Replace the existing local API credential? [y/N] ").lower() != "y":
        return
    username = input("Dedicated API username (also the audit identity): ").strip()
    if not username.isascii() or not username or len(username) > 200 or ":" in username or any(ord(c) < 33 for c in username):
        raise SystemExit("Use 1-200 printable ASCII characters without spaces or colon.")
    for attempt in range(3):
        password = getpass.getpass("Dedicated API password (16+ ASCII characters; not your work password): ")
        if len(password) < 16 or not password.isascii() or any(ord(c) < 32 or ord(c) > 126 for c in password):
            print("Not saved: use at least 16 printable ASCII characters. Try again; typing stays hidden.")
            continue
        if password == getpass.getpass("Confirm API password: "):
            break
        print("Passwords did not match. Try again; nothing saved.")
    else:
        raise SystemExit("No credential saved after three attempts. Run setup again when ready.")
    salt = secrets.token_hex(32)
    config = dict(version=1, username=username, salt=salt, iterations=ITERATIONS,
                  digest=password_digest(password, salt))
    temporary = path.with_suffix(".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(config, stream)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("Local API verifier saved. Enter the same credential privately in the existing connector connection.")


if __name__ == "__main__":
    main()
