#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import secrets
import shlex
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# These defaults are safe starting points, but operators can override them via
# environment variables when adapting the helper to a different witness setup.
DEFAULT_GUARD_RPC_URL = os.getenv("BLURT_GUARD_RPC_URL", "https://rpc.beblurt.com")
DEFAULT_WITNESS_OWNER = os.getenv("BLURT_WITNESS_OWNER", "")
DEFAULT_WITNESS_URL = os.getenv("BLURT_WITNESS_URL", "")
DEFAULT_CONTAINER_NAME = os.getenv("BLURT_WITNESS_CONTAINER", "blurt-witness")
DEFAULT_SAFETY_SECONDS = int(os.getenv("BLURT_WITNESS_SAFE_MARGIN_SECONDS", "45"))
DEFAULT_WALLET_FILE = os.getenv("BLURT_WITNESS_WALLET_FILE", "wallet.json")

NULL_SIGNING_KEY = "BLT1111111111111111111111111111111114T1Anm"
# Override this when the active witness signing public key for the deployment
# differs from the reference one used by @drakernoise.
ACTIVE_SIGNING_KEY = os.getenv("BLURT_ACTIVE_WITNESS_SIGNING_KEY", "")
SLOT_SECONDS = 3

# Canonical defaults. They can be overridden globally with BLURT_WITNESS_PROPS_JSON
# or field-by-field through the environment variables mapped below.
DEFAULT_WITNESS_PROPS = {
    "account_creation_fee": "300.000 BLURT",
    "maximum_block_size": 65536,
    "account_subsidy_budget": 797,
    "account_subsidy_decay": 347321,
    "operation_flat_fee": "0.001 BLURT",
    "bandwidth_kbytes_fee": "0.285 BLURT",
    "proposal_fee": "1000.000 BLURT",
}

WITNESS_PROPS_JSON_ENV = "BLURT_WITNESS_PROPS_JSON"
WITNESS_PROP_ENV_MAP = {
    "account_creation_fee": "BLURT_WITNESS_ACCOUNT_CREATION_FEE",
    "maximum_block_size": "BLURT_WITNESS_MAXIMUM_BLOCK_SIZE",
    "account_subsidy_budget": "BLURT_WITNESS_ACCOUNT_SUBSIDY_BUDGET",
    "account_subsidy_decay": "BLURT_WITNESS_ACCOUNT_SUBSIDY_DECAY",
    "operation_flat_fee": "BLURT_WITNESS_OPERATION_FLAT_FEE",
    "bandwidth_kbytes_fee": "BLURT_WITNESS_BANDWIDTH_KBYTES_FEE",
    "proposal_fee": "BLURT_WITNESS_PROPOSAL_FEE",
}
INT_PROPS = {
    "maximum_block_size",
    "account_subsidy_budget",
    "account_subsidy_decay",
}


@dataclass
class SlotWindow:
    owner: str
    rpc_url: str
    current_witness: str
    current_aslot: int
    next_slot_number: int | None
    eta_seconds: int | None
    safe_margin_seconds: int
    safe_now: bool
    schedule_size: int
    head_block_number: int
    head_block_time: str


def resolve_secrets_file() -> Path:
    override = os.getenv("BLURT_SECRETS_FILE", "").strip()
    if override:
        return Path(override)

    script_dir = Path(__file__).resolve().parent
    # If operators do not want to pass BLURT_SECRETS_FILE explicitly, they can
    # drop one of these files next to the scripts and keep the workflow portable.
    candidates = [script_dir / ".secrets.env", script_dir / "secrets.env", script_dir / ".env"]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise RuntimeError(
        "BLURT_SECRETS_FILE is not set and no local secrets file was found. "
        "Set BLURT_SECRETS_FILE or place .secrets.env/secrets.env beside the scripts."
    )


def require_setting(value: str, env_name: str) -> str:
    resolved = value.strip()
    if resolved:
        return resolved

    raise RuntimeError(
        f"{env_name} is required for this workflow. "
        f"Set {env_name} explicitly in the environment or secrets file."
    )


def load_active_key() -> str:
    env_path = resolve_secrets_file()
    active_key = ""
    with env_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line.startswith("BLURT_ACTIVE_KEY="):
                active_key = line.split("=", 1)[1].strip()
                break
    if not active_key:
        raise RuntimeError(f"BLURT_ACTIVE_KEY not found in {env_path}")
    return active_key


def resolve_container_name(container_name: str | None = None) -> str:
    explicit = (container_name or "").strip()
    if explicit:
        return explicit

    env_name = os.getenv("BLURT_WITNESS_CONTAINER", "").strip()
    if env_name:
        return env_name

    try:
        output = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True, timeout=10)
    except subprocess.SubprocessError as exc:
        raise RuntimeError("Unable to list running docker containers") from exc

    names = [line.strip() for line in output.splitlines() if line.strip()]
    preferred = [name for name in names if name == DEFAULT_CONTAINER_NAME]
    if preferred:
        return preferred[0]

    if "blurtd-go" in names:
        return "blurtd-go"

    suffix_matches = [name for name in names if name.endswith("_blurt-witness")]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    contains_matches = [name for name in names if "blurt-witness" in name]
    if len(contains_matches) == 1:
        return contains_matches[0]

    if suffix_matches:
        raise RuntimeError(
            f"Multiple witness-like containers found: {', '.join(suffix_matches)}. Pass --container-name explicitly."
        )
    if contains_matches:
        raise RuntimeError(
            f"Multiple containers containing blurt-witness found: {', '.join(contains_matches)}. Pass --container-name explicitly."
        )

    raise RuntimeError(
        f"No running witness container found. Expected '{DEFAULT_CONTAINER_NAME}' or '*_blurt-witness'."
    )


def load_witness_props() -> dict[str, Any]:
    props = dict(DEFAULT_WITNESS_PROPS)

    props_json = os.getenv(WITNESS_PROPS_JSON_ENV, "").strip()
    if props_json:
        try:
            parsed = json.loads(props_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{WITNESS_PROPS_JSON_ENV} is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError(f"{WITNESS_PROPS_JSON_ENV} must be a JSON object")
        for key, value in parsed.items():
            if key not in props:
                raise RuntimeError(f"Unsupported witness prop override: {key}")
            props[key] = value

    # Field-by-field overrides are useful when operators want to tweak a single
    # prop without copying the entire JSON object.
    for key, env_name in WITNESS_PROP_ENV_MAP.items():
        raw = os.getenv(env_name, "").strip()
        if not raw:
            continue
        props[key] = int(raw) if key in INT_PROPS else raw

    return props


def rpc_call(rpc_url: str, method: str, params: Any) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    req = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
    if "error" in data:
        raise RuntimeError(f"RPC error for {method}: {data['error']}")
    return data["result"]


def get_dynamic_global_properties(rpc_url: str) -> dict[str, Any]:
    attempts = [
        ("database_api.get_dynamic_global_properties", {}),
        ("condenser_api.get_dynamic_global_properties", []),
    ]
    last_error: Exception | None = None
    for method, params in attempts:
        try:
            result = rpc_call(rpc_url, method, params)
            if isinstance(result, dict):
                return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise RuntimeError(f"Unable to fetch dynamic global properties: {last_error}")


def get_witness_schedule(rpc_url: str) -> dict[str, Any]:
    attempts = [
        ("database_api.get_witness_schedule", {}),
        ("condenser_api.get_witness_schedule", []),
    ]
    last_error: Exception | None = None
    for method, params in attempts:
        try:
            result = rpc_call(rpc_url, method, params)
            if isinstance(result, dict):
                return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise RuntimeError(f"Unable to fetch witness schedule: {last_error}")


def compute_slot_window(
    rpc_url: str = DEFAULT_GUARD_RPC_URL,
    owner: str = DEFAULT_WITNESS_OWNER,
    safe_margin_seconds: int = DEFAULT_SAFETY_SECONDS,
) -> SlotWindow:
    owner = require_setting(owner, "BLURT_WITNESS_OWNER")
    props = get_dynamic_global_properties(rpc_url)
    schedule = get_witness_schedule(rpc_url)
    shuffled = schedule.get("current_shuffled_witnesses") or []
    if not shuffled:
        raise RuntimeError("Witness schedule does not expose current_shuffled_witnesses")

    current_aslot = int(props.get("current_aslot", 0))
    current_witness = str(props.get("current_witness", ""))
    schedule_size = len(shuffled)
    max_safe_margin_seconds = (schedule_size - 1) * SLOT_SECONDS
    if safe_margin_seconds >= max_safe_margin_seconds:
        raise RuntimeError(
            f"Configured safe margin {safe_margin_seconds}s is impossible for this schedule; "
            f"it must be lower than the maximum witness rotation gap of {max_safe_margin_seconds}s."
        )

    next_slot_number = None
    for slot_offset in range(1, schedule_size + 1):
        idx = (current_aslot + slot_offset) % schedule_size
        if shuffled[idx] == owner:
            next_slot_number = slot_offset
            break

    eta_seconds = None if next_slot_number is None else next_slot_number * SLOT_SECONDS
    safe_now = eta_seconds is None or eta_seconds > safe_margin_seconds

    return SlotWindow(
        owner=owner,
        rpc_url=rpc_url,
        current_witness=current_witness,
        current_aslot=current_aslot,
        next_slot_number=next_slot_number,
        eta_seconds=eta_seconds,
        safe_margin_seconds=safe_margin_seconds,
        safe_now=safe_now,
        schedule_size=schedule_size,
        head_block_number=int(props.get("head_block_number", 0)),
        head_block_time=str(props.get("time", "")),
    )


def print_slot_window(window: SlotWindow) -> None:
    print(f"RPC: {window.rpc_url}")
    print(f"Witness owner: {window.owner}")
    print(f"Head block: {window.head_block_number}")
    print(f"Head time: {window.head_block_time}")
    print(f"Current witness: {window.current_witness}")
    print(f"Current aslot: {window.current_aslot}")
    print(f"Schedule size: {window.schedule_size}")
    if window.next_slot_number is None:
        print("Next slot: not found in current shuffled witness set")
    else:
        print(f"Next slot offset: {window.next_slot_number}")
        print(f"ETA seconds: {window.eta_seconds}")
    print(f"Safe margin seconds: {window.safe_margin_seconds}")
    print(f"Safe now: {'yes' if window.safe_now else 'no'}")


def require_safe_window(
    rpc_url: str = DEFAULT_GUARD_RPC_URL,
    owner: str = DEFAULT_WITNESS_OWNER,
    safe_margin_seconds: int = DEFAULT_SAFETY_SECONDS,
) -> SlotWindow:
    window = compute_slot_window(rpc_url=rpc_url, owner=owner, safe_margin_seconds=safe_margin_seconds)
    print_slot_window(window)
    if not window.safe_now:
        raise RuntimeError(
            f"Unsafe witness window: next slot in {window.eta_seconds}s, required margin is {window.safe_margin_seconds}s."
        )
    return window


def reset_wallet_file(container_name: str, wallet_file: str = DEFAULT_WALLET_FILE) -> None:
    subprocess.run(
        ["docker", "exec", container_name, "rm", "-f", wallet_file],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def cli_wallet_update_witness(
    signing_key: str,
    owner: str = DEFAULT_WITNESS_OWNER,
    witness_url: str = DEFAULT_WITNESS_URL,
    container_name: str | None = None,
) -> None:
    owner = require_setting(owner, "BLURT_WITNESS_OWNER")
    witness_url = require_setting(witness_url, "BLURT_WITNESS_URL")
    signing_key = require_setting(signing_key, "BLURT_ACTIVE_WITNESS_SIGNING_KEY")
    active_key = load_active_key()
    wallet_password = os.getenv("BLURT_WITNESS_WALLET_PASSWORD", secrets.token_urlsafe(24))
    props_json = json.dumps(load_witness_props(), separators=(",", ":"))
    resolved_container_name = resolve_container_name(container_name)
    reset_wallet_file(resolved_container_name)
    commands = [
        f'set_password "{wallet_password}"',
        f'unlock "{wallet_password}"',
        f'import_key "{active_key}"',
        f'update_witness "{owner}" "{witness_url}" "{signing_key}" {props_json} true',
    ]
    input_str = "\n".join(commands) + "\n"
    command = (
        "docker exec -i "
        f"{shlex.quote(resolved_container_name)} "
        "/usr/bin/cli_wallet -s ws://127.0.0.1:8090"
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        handle.write(input_str)
        input_path = handle.name
    try:
        process = subprocess.run(
            ["script", "-qefc", command, "/dev/null"],
            stdin=open(input_path, "r", encoding="utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("cli_wallet timed out while updating witness") from exc
    finally:
        try:
            os.unlink(input_path)
        except FileNotFoundError:
            pass

    stdout, stderr = process.stdout, process.stderr
    success_markers = (
        "transaction_id",
        '"block_num":',
        '"expired":false',
        "broadcast_transaction",
    )
    if process.returncode != 0 or not any(marker in stdout for marker in success_markers):
        raise RuntimeError(
            f"cli_wallet failed with code {process.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )

    print(f"Using witness container: {resolved_container_name}")
    print(stdout)
    if stderr.strip():
        print(stderr, file=sys.stderr)
