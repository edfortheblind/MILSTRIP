# Unsigned Pilot Installer

`MILSTRIP.iss` creates one per-user Windows x64 installer. It requires no
administrator rights and installs the self-contained application under the
user's Local AppData, with Start Menu and optional Desktop shortcuts.

The GitHub workflow:

1. runs Python and C# gates;
2. publishes the self-contained Windows application;
3. downloads the immutable Inno Setup 6.7.3 release;
4. verifies its published SHA-256 and Authenticode publisher;
5. compiles the versioned installer;
6. smoke-tests install, launch, in-place reinstall and uninstall;
7. uploads the installer and checksum; and
8. optionally creates a prerelease in this private repository.

## Pilot limitations

- The installer is unsigned. SmartScreen, Defender or organizational EDR may
  warn, block or quarantine it. Never disable security controls to run it.
- SHA-256 detects corruption but does not replace trusted publisher signing.
- The initial workflow tests reinstall of the same version; cross-version
  upgrade/rollback remains a signed-release gate.
- Inno Setup requests a commercial license for commercial/organizational use.
  Confirm licensing before distribution beyond the approved evaluation pilot.
- A GitHub prerelease in this private repository is available only to users
  with repository access.

Production distribution still requires code signing, IT/EDR validation and
the release gates in `docs/delivery/PHASE_2A_AUDIT.md`.
