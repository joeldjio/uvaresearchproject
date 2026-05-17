"""
TelemetryContext — QAbstractListModel exposing per-drone telemetry to QML.

QML accesses it as a ListModel with roles: droneId, lat, lon, alt, speed,
heading, roll, pitch, armed, flightMode, battery, satellites, gpsFix.
"""
from PyQt6.QtCore import (
    QAbstractListModel, QModelIndex, Qt, pyqtSignal,
    pyqtSlot, pyqtProperty, QObject
)


_ROLES = {
    Qt.ItemDataRole.UserRole +  0: b"droneId",
    Qt.ItemDataRole.UserRole +  1: b"lat",
    Qt.ItemDataRole.UserRole +  2: b"lon",
    Qt.ItemDataRole.UserRole +  3: b"altRel",
    Qt.ItemDataRole.UserRole +  4: b"altAmsl",
    Qt.ItemDataRole.UserRole +  5: b"groundspeed",
    Qt.ItemDataRole.UserRole +  6: b"heading",
    Qt.ItemDataRole.UserRole +  7: b"roll",
    Qt.ItemDataRole.UserRole +  8: b"pitch",
    Qt.ItemDataRole.UserRole +  9: b"armed",
    Qt.ItemDataRole.UserRole + 10: b"flightMode",
    Qt.ItemDataRole.UserRole + 11: b"batteryPct",
    Qt.ItemDataRole.UserRole + 12: b"batteryV",
    Qt.ItemDataRole.UserRole + 13: b"satellites",
    Qt.ItemDataRole.UserRole + 14: b"gpsFix",
    Qt.ItemDataRole.UserRole + 15: b"climb",
    Qt.ItemDataRole.UserRole + 16: b"throttle",
    Qt.ItemDataRole.UserRole + 17: b"connected",
    Qt.ItemDataRole.UserRole + 18: b"autopilot",
    Qt.ItemDataRole.UserRole + 19: b"vehicleType",
    Qt.ItemDataRole.UserRole + 20: b"systemStatus",
    Qt.ItemDataRole.UserRole + 21: b"firmwareVersion",
    Qt.ItemDataRole.UserRole + 22: b"boardVersion",
    Qt.ItemDataRole.UserRole + 23: b"vendorId",
    Qt.ItemDataRole.UserRole + 24: b"productId",
    Qt.ItemDataRole.UserRole + 25: b"connectionString",
    Qt.ItemDataRole.UserRole + 26: b"droneType",
    Qt.ItemDataRole.UserRole + 27: b"fsmState",
}

_ROLE_KEYS = {v: k for k, v in _ROLES.items()}

_SNAP_MAP = {
    b"lat":        "lat",
    b"lon":        "lon",
    b"altRel":     "alt_rel",
    b"altAmsl":    "alt",
    b"groundspeed":"groundspeed",
    b"heading":    "yaw",
    b"roll":       "roll",
    b"pitch":      "pitch",
    b"armed":      "armed",
    b"flightMode": "flight_mode",
    b"batteryPct": "battery_pct",
    b"batteryV":   "battery_v",
    b"satellites": "satellites",
    b"gpsFix":     "gps_fix",
    b"climb":      "climb",
    b"throttle":   "throttle",
    b"connected":  "connected",
    b"autopilot":  "autopilot",
    b"vehicleType": "vehicle_type",
    b"systemStatus": "system_status",
    b"firmwareVersion": "firmware_version",
    b"boardVersion": "board_version",
    b"vendorId": "vendor_id",
    b"productId": "product_id",
    b"connectionString": "connectionString",
    b"droneType": "droneType",
    b"fsmState": "fsmState",
}


class TelemetryModel(QAbstractListModel):
    """
    ListModel where each row is one drone's latest telemetry snapshot.
    Updated via update_all(snapshots: dict).
    """

    countChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._order: list  = []   # ordered drone IDs
        self._data:  dict  = {}   # {drone_id: snap_dict}

    # ── QAbstractListModel implementation ─────────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._order)

    def roleNames(self) -> dict:
        return _ROLES

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._order):
            return None
        did  = self._order[index.row()]
        snap = self._data.get(did, {})
        role_name = _ROLES.get(role)
        if role_name == b"droneId":
            return did
        snap_key = _SNAP_MAP.get(role_name)
        if snap_key:
            return snap.get(snap_key, 0 if role_name not in (b"flightMode", b"autopilot", b"vehicleType", b"firmwareVersion", b"boardVersion", b"connectionString", b"droneType", b"fsmState") else "UNKNOWN")
        return None

    # ── Public API ────────────────────────────────────────────────────────

    def update_all(self, snapshots: dict) -> None:
        """Called from Python with {drone_id: snap_dict}."""
        new_ids  = set(snapshots.keys())
        old_ids  = set(self._order)
        added    = new_ids - old_ids
        removed  = old_ids - new_ids

        for did in removed:
            row = self._order.index(did)
            self.beginRemoveRows(QModelIndex(), row, row)
            self._order.remove(did)
            del self._data[did]
            self.endRemoveRows()
            self.countChanged.emit()

        for did in sorted(added):
            row = len(self._order)
            self.beginInsertRows(QModelIndex(), row, row)
            self._order.append(did)
            self._data[did] = snapshots[did]
            self.endInsertRows()
            self.countChanged.emit()

        # Differential update: only emit dataChanged for roles whose
        # value actually changed since the last snapshot. Avoids
        # re-evaluating ~17 QML bindings per drone per tick.
        all_role_ids = list(_ROLES.keys())
        for row, did in enumerate(self._order):
            if did not in snapshots:
                continue
            new_snap = snapshots[did]
            old_snap = self._data.get(did, {})
            changed_roles: list = []
            for role_id, role_name in _ROLES.items():
                if role_name == b"droneId":
                    continue
                snap_key = _SNAP_MAP.get(role_name)
                if not snap_key:
                    continue
                if old_snap.get(snap_key) != new_snap.get(snap_key):
                    changed_roles.append(role_id)
            self._data[did] = new_snap
            if changed_roles:
                idx = self.index(row, 0)
                # If everything changed, emit the full set so QML
                # caches don't bother to inspect roles.
                if len(changed_roles) >= len(all_role_ids) - 1:
                    self.dataChanged.emit(idx, idx, all_role_ids)
                else:
                    self.dataChanged.emit(idx, idx, changed_roles)

    @pyqtSlot(str, result="QVariant")
    def snapshotFor(self, drone_id: str) -> dict:
        return self._data.get(drone_id, {})

    @pyqtProperty(int, notify=countChanged)
    def count(self) -> int:
        return len(self._order)
