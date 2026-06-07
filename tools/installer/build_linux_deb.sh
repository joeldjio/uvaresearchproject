#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Build a Debian package for uavresearch gcs on Ubuntu 22.04 / Jammy.

Usage:
  tools/installer/build_linux_deb.sh [--skip-bundle]

Options:
  --skip-bundle   Reuse an existing dist/UAVResearchGCS bundle.
EOF
}

SKIP_BUNDLE=0
case "${1-}" in
  "") ;;
  --skip-bundle) SKIP_BUNDLE=1 ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unknown argument: ${1}" >&2; usage >&2; exit 2 ;;
esac

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd -- "${SCRIPT_DIR}/../.." && pwd)
OUT_DIR="${SCRIPT_DIR}/out"
PKG_TMP_ROOT="${PROJECT_ROOT}/build/linux-deb"
DIST_DIR="${PROJECT_ROOT}/dist/UAVResearchGCS"
ASSETS_DIR="${SCRIPT_DIR}/assets"

cd "${PROJECT_ROOT}"

APP_VERSION=$(python - <<'PY'
from tools.ui._version import VERSION
print(VERSION)
PY
)

PACKAGE_NAME="uavresearch-gcs"
PACKAGE_DIR="${PKG_TMP_ROOT}/${PACKAGE_NAME}_${APP_VERSION}_amd64"
PACKAGE_FILE="${OUT_DIR}/${PACKAGE_NAME}_${APP_VERSION}_amd64_jammy.deb"

mkdir -p "${OUT_DIR}"
rm -rf "${PACKAGE_DIR}"
mkdir -p \
  "${PACKAGE_DIR}/DEBIAN" \
  "${PACKAGE_DIR}/opt/${PACKAGE_NAME}" \
  "${PACKAGE_DIR}/usr/bin" \
  "${PACKAGE_DIR}/usr/share/applications" \
  "${PACKAGE_DIR}/usr/share/icons/hicolor/256x256/apps"

if [[ "${SKIP_BUNDLE}" -eq 0 ]]; then
  echo "[1/3] Generating branding assets"
  python tools/installer/icon/make_assets.py

  echo "[2/3] Building Linux PyInstaller bundle"
  pyinstaller tools/installer/specs/uavresearch_gcs.spec --noconfirm --clean
else
  echo "[1/3] Reusing existing PyInstaller bundle (--skip-bundle)"
fi

if [[ ! -d "${DIST_DIR}" ]]; then
  echo "Missing PyInstaller bundle: ${DIST_DIR}" >&2
  exit 1
fi

if [[ ! -f "${ASSETS_DIR}/uavresearch_logo_256.png" ]]; then
  echo "Missing generated logo asset: ${ASSETS_DIR}/uavresearch_logo_256.png" >&2
  exit 1
fi

echo "[3/3] Packaging Debian installer"
cp -a "${DIST_DIR}/." "${PACKAGE_DIR}/opt/${PACKAGE_NAME}/"
install -m 0644 "${ASSETS_DIR}/uavresearch_logo_256.png" \
  "${PACKAGE_DIR}/usr/share/icons/hicolor/256x256/apps/${PACKAGE_NAME}.png"

cat > "${PACKAGE_DIR}/usr/bin/${PACKAGE_NAME}" <<'EOF'
#!/usr/bin/env bash
exec "/opt/uavresearch-gcs/uavresearch gcs" "$@"
EOF
chmod 0755 "${PACKAGE_DIR}/usr/bin/${PACKAGE_NAME}"

cat > "${PACKAGE_DIR}/usr/share/applications/${PACKAGE_NAME}.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=uavresearch gcs
Comment=UAVResearch ground control station
Exec=uavresearch-gcs
Icon=uavresearch-gcs
Terminal=false
Categories=Science;Engineering;
StartupNotify=true
EOF

cat > "${PACKAGE_DIR}/DEBIAN/control" <<EOF
Package: ${PACKAGE_NAME}
Version: ${APP_VERSION}
Section: science
Priority: optional
Architecture: amd64
Maintainer: UAVResearch <djiojoel2@gmail.com>
Depends: libegl1, libgl1, libdbus-1-3, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xinerama0, libxcb-xfixes0
Description: uavresearch gcs ground control station
 Self-contained PyInstaller build of the UAVResearch ground control station
 for Ubuntu 22.04 LTS (Jammy).
EOF

find "${PACKAGE_DIR}" -type d -exec chmod 0755 {} +

dpkg-deb --build --root-owner-group "${PACKAGE_DIR}" "${PACKAGE_FILE}"
echo "Wrote ${PACKAGE_FILE}"
