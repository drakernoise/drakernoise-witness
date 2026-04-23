#!/usr/bin/env python3
from __future__ import annotations

import sys

from witness_guard import main as guard_main


if __name__ == "__main__":
    sys.exit(guard_main(["check", *sys.argv[1:]]))
