#!/usr/bin/env python3
from __future__ import annotations

import sys

from witness_guard import main as guard_main


if __name__ == "__main__":
    try:
        sys.exit(guard_main(["enable", *sys.argv[1:]]))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
