"""
Workaround for a bug in Python 3.10.0 - 3.10.3 ``dis._get_const_info`` that
crashes with ``IndexError: tuple index out of range`` when PyInstaller
analyses certain wheels (most notably ``setuptools._vendor`` and ``lxml``
on Windows).

Fixed upstream in CPython 3.10.4 (bpo-45757). Until everyone is on
3.10.4+ / 3.11+, importing this module replaces the buggy helper with a
defensive version that returns a placeholder instead of crashing the
whole build.

Spec files apply the patch by doing:

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(SPECPATH).resolve()))
    import _dis_patch  # noqa: F401
"""
from __future__ import annotations

import dis
import sys


def _safe_get_const_info(const_index, const_list):
    argval = const_index
    if const_list is not None:
        try:
            argval = const_list[const_index]
        except IndexError:
            # Bytecode references a const slot that doesn't exist in the
            # interpreter's current view of the code object. Skip cleanly
            # so PyInstaller's bytecode walker can move on.
            argval = f"<const #{const_index}>"
    return argval, repr(argval)


if sys.version_info < (3, 10, 4):
    dis._get_const_info = _safe_get_const_info  # type: ignore[assignment]
    print(
        f"[_dis_patch] Patched dis._get_const_info for Python "
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} "
        "(bpo-45757 workaround)."
    )
