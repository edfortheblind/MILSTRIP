"""Privately test the owner's API credential directly, bypassing the gateway."""
import getpass
import sys

import httpx


def main():
    username = input("API username [milstrip-app]: ").strip() or "milstrip-app"
    password = getpass.getpass("API password (hidden; not saved): ")
    try:
        with httpx.Client(timeout=10, trust_env=False, follow_redirects=False) as client:
            response = client.get("http://127.0.0.1:8000/api/v1/health", auth=(username, password))
    except httpx.HTTPError:
        print("Local API connection failed. No credential was saved or displayed.")
        return 1
    print(f"Local API HTTP status: {response.status_code}")
    if response.status_code == 200:
        print("Credential accepted locally. Use this same username/password in the selected gateway connection.")
        return 0
    if response.status_code == 401:
        print("Credential rejected locally. Re-enter it or rerun Set-LocalApiCredential.ps1 privately, then update the connector connection to match.")
    elif response.status_code == 503:
        print("Local API configuration unavailable. Report this status; do not share credentials.")
    else:
        print("Unexpected local status. Report only the status number.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
