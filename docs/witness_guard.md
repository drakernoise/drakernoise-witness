# Witness Guard Workflow

## Purpose

This workflow exists to enable or disable the witness more safely than direct manual `cli_wallet` use.

The goal is to reduce the chance of losing blocks during witness toggling by checking whether the current schedule window is considered safe before broadcasting a `witness_update`.

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

- witness owner: `drakernoise`
- witness website:
  - `https://drakernoise.com/blurt_witness/`
- timing RPC:
  - `https://rpc.beblurt.com`
- safe margin:
  - `90` seconds

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

If `BLURT_SECRETS_FILE` is not set, the scripts will look for:

- `.secrets.env`
- `secrets.env`
- `.env`

in the same directory as the scripts.

## Important Notes

- The witness Active key must remain server-side only.
- Browser-side enable/disable logic is not considered safe.
- The guarded scripts prefer container autodetection over hardcoded container names.
- Canonical witness props are centralized in the shared library, but they can be overridden with environment variables when the operator needs different values.
- The scripts reset the wallet file inside the container before importing the Active key, so they do not depend on a pre-existing wallet state.

## Legacy Script Status

The old activation helper was retired because it relied on:

- a stale public key
- a fixed container name
- a weaker manual flow

The guarded workflow supersedes that approach.
