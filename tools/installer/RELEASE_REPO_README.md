# uavresearch gcs Releases

This repository is the public release channel for **uavresearch gcs**.

It contains published installer files and release notes used by the in-app updater.

## What this repository contains

- uavresearch gcs installer releases
- Release notes
- Update metadata through GitHub Releases

## What this repository does not contain

This repository does **not** contain the application source code.

The source code is maintained in a private repository.

Do not upload:

- source code
- Python files
- build scripts
- license generator scripts
- license secrets
- GitHub tokens
- private internal notes

## Downloads

Installers are available under the **Releases** section:

```text
https://github.com/joeldjio/uavresearch-gcs-releases/releases
```

Download the newest release assets named like:

```text
uavresearch-gcs-setup-X.Y.Z.exe
uavresearch-gcs_X.Y.Z_amd64_jammy.deb
```

Examples:

```text
uavresearch-gcs-setup-0.3.1.exe
uavresearch-gcs_0.3.1_amd64_jammy.deb
```

## Updates

uavresearch gcs checks this repository for new GitHub Releases.

The in-app updater currently handles the Windows installer only.

The in-app updater looks for installer assets whose file name starts with:

```text
uavresearch-gcs-setup-
```

and ends with:

```text
.exe
```

If the asset name does not match this pattern, the updater will not find the update.

## License

uavresearch gcs is commercial software with a built-in trial period.

To request a license key, contact:

```text
djiojoel2@gmail.com
```

## Release asset naming rule

Always upload Windows installers using this format:

```text
uavresearch-gcs-setup-X.Y.Z.exe
```

Do not rename the installer to random names like:

```text
setup.exe
UAVGCS.exe
installer-latest.exe
```

Those names will not be detected by the in-app updater.

## Maintainer checklist

For every release:

1. Build the installer in the private source repository.
2. Create a new GitHub Release in this repository.
3. Use a version tag like `v0.3.1`.
4. Upload `uavresearch-gcs-setup-X.Y.Z.exe` as the Windows release asset.
5. Upload `uavresearch-gcs_X.Y.Z_amd64_jammy.deb` as the Linux release asset.
6. Add short release notes.
7. Publish the release.
8. Test the Windows in-app updater from an installed uavresearch gcs copy.
