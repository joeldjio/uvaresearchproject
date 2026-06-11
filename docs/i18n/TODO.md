# i18n TODO

## Pending Translations

### HelpPanel.qml - Complete Translation Needed

The `tools/ui/qml/panels/HelpPanel.qml` file contains extensive German documentation text (~400+ lines) in the `body` fields of HelpSection components. This needs to be fully translated to English.

**Status**: Partially translated
- ✅ Header and titles translated
- ✅ Glossary translated  
- ✅ Footer messages translated
- ❌ HelpSection body content (lines 188-641) still in German

**Sections to translate**:
1. Quickstart (5 Steps to First Mission)
2. Global Concepts
3. Tab: Map
4. Tab: Telemetry (Dashboard)
5. Tab: Swarm Control
6. Tab: Safety / APF
7. Tab: Gimbal / Camera
8. Tab: ROS2 / uXRCE-DDS
9. Tab: Scenario (Experiment Runner)
10. Tab: Flight Log
11. Tab: System Log
12. InstrBar (top strip)
13. Conventions, Gotchas & Troubleshooting
14. Keyboard & Mouse Shortcuts

**Approach**: Each HelpSection body contains HTML-formatted German text that should be wrapped with `qsTr()` and translated to English. The content is technical documentation, so translations should maintain technical accuracy.

**Estimated effort**: 2-3 hours for complete translation

## Notes

- All other panels have been translated
- Translation infrastructure is complete and working
- Language switcher is functional
- Documentation and tests are in place