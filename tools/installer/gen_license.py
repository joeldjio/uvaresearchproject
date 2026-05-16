"""
RZ GCS — license key generator (offline, no server).

Use this script when a customer's free trial expires and they want to
keep using the software. The generated key is purely a function of the
shared ``LICENSE_SECRET`` in ``tools/ui/_version.py`` and the chosen
expiry date — the app validates it locally on activation.

Examples
--------
Hand-pick an expiry date:

    python tools\\installer\\gen_license.py 2026-12-31

Trial extension (90 days from today):

    python tools\\installer\\gen_license.py --days 90

Annotate the output with a customer label (for your own records — the
key itself does NOT embed the customer name):

    python tools\\installer\\gen_license.py --customer "Acme Drones" 2027-01-31
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

# Make ``tools.ui.license`` importable when run from anywhere.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from tools.ui._version import LICENSE_SECRET, TRIAL_DAYS  # noqa: E402
from tools.ui.license import generate_key                  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "expiry",
        nargs="?",
        help="Expiry date (inclusive) in YYYY-MM-DD format.",
    )
    g.add_argument(
        "--days",
        type=int,
        help="Generate a key that expires N days from today.",
    )
    p.add_argument(
        "--customer",
        help="Customer label printed alongside the key (record-keeping only).",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    if args.days is not None:
        if args.days <= 0:
            print("ERROR: --days must be positive.", file=sys.stderr)
            return 2
        expiry = date.today() + timedelta(days=args.days)
    else:
        try:
            expiry = date.fromisoformat(args.expiry)
        except ValueError:
            print(
                f"ERROR: invalid expiry '{args.expiry}'. Use YYYY-MM-DD.",
                file=sys.stderr,
            )
            return 2

    if expiry < date.today():
        print(
            f"WARNING: expiry {expiry.isoformat()} is in the past; "
            "the customer will not be able to activate this key.",
            file=sys.stderr,
        )

    key = generate_key(expiry)

    bar = "─" * 60
    print()
    print(f"┌{bar}┐")
    print(f"│  RZ GCS license key{' ' * (bar.__len__() - 19)}│")
    print(f"├{bar}┤")
    if args.customer:
        print(f"│  Customer : {args.customer}")
    print(f"│  Expires  : {expiry.isoformat()}  (inclusive)")
    print(f"│  Key      : {key}")
    print(f"└{bar}┘")
    print()
    print("Send the 'Key' line to the customer. They paste it into the")
    print("RZ GCS activation dialog — no internet required.")
    print()
    if LICENSE_SECRET.startswith("rz-solutions-dev-secret"):
        print(
            "⚠  The LICENSE_SECRET in tools/ui/_version.py is still the\n"
            "   development default. ROTATE it before shipping keys to\n"
            "   paying customers, then rebuild the installer.",
            file=sys.stderr,
        )
    print(
        f"   (Default trial length without a key: {TRIAL_DAYS} days "
        "from first launch.)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
