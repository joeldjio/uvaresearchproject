# uavresearch gcs 0.3.1

uavresearch gcs 0.3.1 release.

## Highlights

- Fixes an internal `SafetyContext` position-state inconsistency used by APF avoidance logic.
- Optimizes installer asset generation and improves Pillow compatibility.
- Adds a direct Ubuntu 22.04 / Jammy Debian build flow.
- Extends GitHub Actions to publish a Windows installer and a Jammy `.deb` artifact.
- Expands release and installer documentation for Windows and Linux maintainers.

## Release assets

Upload these files as release assets:

```text
uavresearch-gcs-setup-0.3.1.exe
uavresearch-gcs_0.3.1_amd64_jammy.deb
```

## Notes

- The in-app updater currently detects and installs the Windows `.exe` asset only.
- The Jammy `.deb` is provided as a direct download for Linux users.
- Build the Windows installer on Windows and the Jammy package on Ubuntu 22.04.
