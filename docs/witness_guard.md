# Witness Guard Workflow

## Purpose

This workflow exists to enable or disable the witness more safely than direct manual `cli_wallet` use.

The goal is to reduce the chance of losing blocks during witness toggling by checking whether the current schedule window is considered safe before broadcasting a `witness_update`.

## Included Scripts

- [`scripts/check_witness_window.py`](../scripts/check_witness_window.py)
  - prints the current slot window and exits with `SAFE` or `UNSAFE`
- [`scripts/disable_witness_guarded.py`](../scripts/disable_witness_guarded.py)
  - switches the witness to `NULL_SIGNING_KEY` only if the window is safe
- [`scripts/activate_witness_guarded.py`](../scripts/activate_witness_guarded.py)
  - restores the configured public signing key only if the window is safe
- [`scripts/witness_guard_lib.py`](../scripts/witness_guard_lib.py)
  - shared logic for schedule checks, wallet handling and `cli_wallet` execution
- [`scripts/secrets.env.example`](../scripts/secrets.env.example)
  - example server-side env file for the guarded scripts

## Requirements

The guard scripts are designed to run on the witness host or on a host that can reach the witness container directly.

You need:

- Python 3
- Docker CLI access
- a witness image that includes `cli_wallet`
- `script` from `util-linux`
  - used to run `cli_wallet` under a pseudo-TTY
- a server-side env file containing your own Active key

The scripts only use the Python standard library. No `pip install` step is required.

## Operational Model

The guarded workflow performs these steps:

1. Query a trusted RPC endpoint for dynamic global properties and witness schedule.
2. Estimate whether the current time is far enough from the witness's next slot.
3. If the timing is unsafe, abort.
4. If the timing is safe, broadcast the `witness_update` through the local witness container.

## Expected Components

The guarded flow is built around:

- a shared library for schedule checks and `cli_wallet` broadcast handling
- a check command for `SAFE` / `UNSAFE`
- an activation command
- a deactivation command

## Intended Defaults

- timing RPC:
  - `https://rpc.beblurt.com`
- safe margin:
  - `45` seconds

Witness-specific values are intentionally not hardcoded anymore:

- `BLURT_WITNESS_OWNER`
- `BLURT_WITNESS_URL`
- `BLURT_ACTIVE_WITNESS_SIGNING_KEY`

## Environment Variables

The workflow can be adapted without editing the code:

- `BLURT_SECRETS_FILE`
  - path to the env file containing `BLURT_ACTIVE_KEY`
- `BLURT_WITNESS_CONTAINER`
  - explicit witness container name
- `BLURT_GUARD_RPC_URL`
  - RPC endpoint used for schedule checks
- `BLURT_WITNESS_OWNER`
  - witness account name
- `BLURT_WITNESS_URL`
  - witness website used in `witness_update`
- `BLURT_ACTIVE_WITNESS_SIGNING_KEY`
  - public witness key used for guarded activation
- `BLURT_WITNESS_SAFE_MARGIN_SECONDS`
  - minimum safe distance to the next slot
- `BLURT_WITNESS_WALLET_FILE`
  - wallet file path inside the container, default `wallet.json`
- `BLURT_WITNESS_WALLET_PASSWORD`
  - optional temporary wallet password override
- `BLURT_WITNESS_PROPS_JSON`
  - full JSON object overriding witness props
- `BLURT_WITNESS_ACCOUNT_CREATION_FEE`
- `BLURT_WITNESS_MAXIMUM_BLOCK_SIZE`
- `BLURT_WITNESS_ACCOUNT_SUBSIDY_BUDGET`
- `BLURT_WITNESS_ACCOUNT_SUBSIDY_DECAY`
- `BLURT_WITNESS_OPERATION_FLAT_FEE`
- `BLURT_WITNESS_BANDWIDTH_KBYTES_FEE`
- `BLURT_WITNESS_PROPOSAL_FEE`

Default note:

- on Blurt, 21 witnesses x 3 seconds per slot means the maximum full rotation gap is `63` seconds
- the safe margin must therefore stay below `63` seconds
- the default `45` seconds is deliberate and can still be overridden per environment

If `BLURT_SECRETS_FILE` is not set, the scripts will look for:

- `.secrets.env`
- `secrets.env`
- `.env`

in the same directory as the scripts.

Minimum operator configuration:

- `BLURT_ACTIVE_KEY`
- `BLURT_WITNESS_OWNER`
- `BLURT_WITNESS_URL`
- `BLURT_ACTIVE_WITNESS_SIGNING_KEY`

## Minimal Setup

Create a local secrets file from the example:

```bash
cd scripts
cp secrets.env.example .secrets.env
chmod 600 .secrets.env
```

Then edit `.secrets.env` with your own values.

## How To Run

From the `scripts/` directory:

```bash
python3 check_witness_window.py
python3 disable_witness_guarded.py
python3 activate_witness_guarded.py
```

If autodetection does not find the correct container, either export `BLURT_WITNESS_CONTAINER` or pass it explicitly:

```bash
python3 disable_witness_guarded.py --container-name blurtd
python3 activate_witness_guarded.py --container-name blurtd
```

Typical operational order:

1. `python3 check_witness_window.py`
2. `python3 disable_witness_guarded.py`
3. perform the upgrade, replay, bootstrap or maintenance task
4. confirm the node is healthy again
5. `python3 check_witness_window.py`
6. `python3 activate_witness_guarded.py`

## Important Notes

- The witness Active key must remain server-side only.
- Browser-side enable/disable logic is not considered safe.
- The guarded scripts prefer container autodetection over hardcoded container names.
- The guard RPC must be reachable from the host where the scripts run.
- The scripts fail fast if witness-specific values are missing instead of silently defaulting to `@drakernoise`.
- Canonical witness props are centralized in the shared library, but they can be overridden with environment variables when the operator needs different values.
- The scripts reset the wallet file inside the container before importing the Active key, so they do not depend on a pre-existing wallet state.
- The helper uses `script` to run `cli_wallet` under a PTY because plain stdin piping is not reliable on every witness image.
