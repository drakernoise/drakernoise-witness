#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from witness_guard_lib import (
    ACTIVE_SIGNING_KEY,
    DEFAULT_GUARD_RPC_URL,
    DEFAULT_SAFETY_SECONDS,
    DEFAULT_WITNESS_OWNER,
    cli_wallet_update_witness,
    require_safe_window,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enable a witness with a guarded schedule check before broadcasting witness_update."
    )
    parser.add_argument("--rpc-url", default=DEFAULT_GUARD_RPC_URL)
    parser.add_argument("--witness", default=DEFAULT_WITNESS_OWNER, help="Witness account name.")
    parser.add_argument("--container-name")
    parser.add_argument("--safe-margin-seconds", type=int, default=DEFAULT_SAFETY_SECONDS)
    parser.add_argument("--signing-key", default=ACTIVE_SIGNING_KEY, help="Public witness signing key.")
    args = parser.parse_args()

    require_safe_window(
        rpc_url=args.rpc_url,
        owner=args.witness,
        safe_margin_seconds=args.safe_margin_seconds,
    )
    cli_wallet_update_witness(
        signing_key=args.signing_key,
        owner=args.witness,
        container_name=args.container_name,
    )
    print("Witness enabled with slot guard.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
