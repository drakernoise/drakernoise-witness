#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from witness_guard_lib import (
    DEFAULT_GUARD_RPC_URL,
    DEFAULT_SAFETY_SECONDS,
    DEFAULT_WITNESS_OWNER,
    compute_slot_window,
    print_slot_window,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estimate whether it is currently safe to enable or disable a witness."
    )
    parser.add_argument("--rpc-url", default=DEFAULT_GUARD_RPC_URL)
    parser.add_argument("--witness", default=DEFAULT_WITNESS_OWNER)
    parser.add_argument("--safe-margin-seconds", type=int, default=DEFAULT_SAFETY_SECONDS)
    parser.add_argument("--quiet", action="store_true", help="Only emit the final SAFE/UNSAFE line.")
    args = parser.parse_args()

    window = compute_slot_window(
        rpc_url=args.rpc_url,
        owner=args.witness,
        safe_margin_seconds=args.safe_margin_seconds,
    )
    if not args.quiet:
        print_slot_window(window)
    print("SAFE" if window.safe_now else "UNSAFE")
    return 0 if window.safe_now else 2


if __name__ == "__main__":
    sys.exit(main())
