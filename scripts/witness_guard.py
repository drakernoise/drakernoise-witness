#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from witness_guard_lib import (
    ACTIVE_SIGNING_KEY,
    DEFAULT_GUARD_RPC_URL,
    DEFAULT_SAFETY_SECONDS,
    DEFAULT_WITNESS_OWNER,
    NULL_SIGNING_KEY,
    cli_wallet_update_witness,
    compute_slot_window,
    print_slot_window,
    require_safe_window,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Guarded witness operations with safe-window checks."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_args(subparser: argparse.ArgumentParser, include_container: bool = False) -> None:
        subparser.add_argument(
            "--rpc-url",
            default=DEFAULT_GUARD_RPC_URL,
            help="RPC endpoint to force. Use 'auto' or omit it to select the best configured RPC.",
        )
        subparser.add_argument("--witness", default=DEFAULT_WITNESS_OWNER, help="Witness account name.")
        subparser.add_argument("--safe-margin-seconds", type=int, default=DEFAULT_SAFETY_SECONDS)
        if include_container:
            subparser.add_argument("--container-name")

    check_parser = subparsers.add_parser(
        "check",
        help="Inspect the current slot window without changing witness state.",
    )
    add_common_args(check_parser)
    check_parser.add_argument("--quiet", action="store_true", help="Only emit the final SAFE/UNSAFE line.")

    disable_parser = subparsers.add_parser(
        "disable",
        help="Disable a witness only when the current schedule window is considered safe.",
    )
    add_common_args(disable_parser, include_container=True)

    enable_parser = subparsers.add_parser(
        "enable",
        help="Enable a witness with a guarded schedule check before broadcasting witness_update.",
    )
    add_common_args(enable_parser, include_container=True)
    enable_parser.add_argument(
        "--signing-key",
        default=ACTIVE_SIGNING_KEY,
        help="Public witness signing key.",
    )

    return parser


def run_check(args: argparse.Namespace) -> int:
    window = compute_slot_window(
        rpc_url=args.rpc_url,
        owner=args.witness,
        safe_margin_seconds=args.safe_margin_seconds,
    )
    if not args.quiet:
        print_slot_window(window)
    print("SAFE" if window.safe_now else "UNSAFE")
    return 0 if window.safe_now else 2


def run_disable(args: argparse.Namespace) -> int:
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


def run_enable(args: argparse.Namespace) -> int:
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        return run_check(args)
    if args.command == "disable":
        return run_disable(args)
    if args.command == "enable":
        return run_enable(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
