# RZ GCS Releases

This repository is the public release channel for **RZ GCS**.

It contains published installer files and release notes used by the in-app updater.

## What this repository contains

- RZ GCS installer releases
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
https://github.com/joeldjio/rz-gcs-releases/releases
```

Download the newest Windows installer asset named like:

```text
RZ-GCS-Setup-X.Y.Z.exe
```

Example:

```text
RZ-GCS-Setup-0.3.0.exe
```

## Updates

RZ GCS checks this repository for new GitHub Releases.

The in-app updater looks for installer assets whose file name starts with:

```text
RZ-GCS-Setup-
```

and ends with:

```text
.exe
```

If the asset name does not match this pattern, the updater will not find the update.

## License

RZ GCS is commercial software with a built-in trial period.

To request a license key, contact:

```text
djiojoel2@gmail.com
```

## Release asset naming rule

Always upload Windows installers using this format:

```text
RZ-GCS-Setup-X.Y.Z.exe
```

Do not rename the installer to random names like:

```text
setup.exe
RZGCS.exe
installer-latest.exe
```

Those names will not be detected by the in-app updater.

## Maintainer checklist

For every release:

1. Build the installer in the private source repository.
2. Create a new GitHub Release in this repository.
3. Use a version tag like `v0.3.0`.
4. Upload `RZ-GCS-Setup-X.Y.Z.exe` as the release asset.
5. Add short release notes.
6. Publish the release.
7. Test the in-app updater from an installed RZ GCS copy.
