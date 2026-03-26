#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from witness_guard_lib import (
    DEFAULT_GUARD_RPC_URL,
    DEFAULT_SAFETY_SECONDS,
    DEFAULT_WITNESS_OWNER,
    NULL_SIGNING_KEY,
    cli_wallet_update_witness,
    require_safe_window,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Disable a witness only when the current schedule window is considered safe."
    )
    parser.add_argument("--rpc-url", default=DEFAULT_GUARD_RPC_URL)
    parser.add_argument("--witness", default=DEFAULT_WITNESS_OWNER)
    parser.add_argument("--container-name")
    parser.add_argument("--safe-margin-seconds", type=int, default=DEFAULT_SAFETY_SECONDS)
    args = parser.parse_args()

    require_safe_window(
        rpc_url=args.rpc_url,
        owner=args.witness,
        safe_margin_seconds=args.safe_margin_seconds,
    )
    cli_wallet_update_witness(
        signing_key=NULL_SIGNING_KEY,
        owner=args.witness,
        container_name=args.container_name,
    )
    print("Witness disabled with slot guard.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
