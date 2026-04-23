# Witness Bootstrap Guide

This guide shows a practical witness bootstrap flow based on:

- Saboin's recommended 0.9.0 witness upgrade process
- the guarded enable/disable helpers in this repository
- an optional fast path using a prebuilt blockchain snapshot

## Before You Start

You need:

- Docker installed on the witness host
- `lz4` installed if you use Saboin's presynced archive
- your own witness configuration values
- your own witness Active key available only on the server

Important:

- never publish your witness `config.ini`
- never publish your Active key
- never publish a snapshot that contains `config.ini`, `wallet.json`, or other secrets

## Guarded Witness Toggle

This repository includes safer witness toggle helpers:

- `scripts/check_witness_window.py`
- `scripts/disable_witness_guarded.py`
- `scripts/activate_witness_guarded.py`

Prepare a local secrets file from:

- `scripts/secrets.env.example`

Example:

```bash
cp scripts/secrets.env.example scripts/.secrets.env
chmod 600 scripts/.secrets.env
```

Then edit it with your real values.

Before any upgrade or snapshot operation:

```bash
cd scripts
python3 check_witness_window.py
python3 disable_witness_guarded.py
```

After the node is back and stable:

```bash
cd scripts
python3 check_witness_window.py
python3 activate_witness_guarded.py
```

If autodetection does not find your witness container, either set
`BLURT_WITNESS_CONTAINER` or pass `--container-name <name>` explicitly.

## Recommended Upgrade Flow

Saboin's base recommendation for 0.9.0 is still solid:

1. Disable the witness first.
2. Pull the latest witness image.
3. Remove the old container.
4. Replace the local blockchain with a presynced one.
5. Start the witness again.
6. Re-enable the witness only after the node is healthy.

## Option A: Fast Path With A Sanitized Snapshot

Use this only with a public snapshot that contains blockchain data only and no secrets.

Expected contents:

- `blurt-witness-data/blockchain/`

Do not use a snapshot if it contains:

- `config.ini`
- `wallet.json`
- `logs/`
- `p2p/`

Recommended publication layout:

Use the canonical object path under `/drakernoise/` to avoid cache edge cases on the short redirect path.

Current published snapshot:

- dated file:
  - `https://images.drakernoise.com/drakernoise/blurt/witness-snapshots/blurt-witness-blockchain-20260423-114147.tar.zst`
- dated checksum:
  - `https://images.drakernoise.com/drakernoise/blurt/witness-snapshots/blurt-witness-blockchain-20260423-114147.tar.zst.sha256`
- stable latest file:
  - `https://images.drakernoise.com/drakernoise/blurt/witness-snapshots/latest-blockchain.tar.zst`
- stable latest checksum:
  - `https://images.drakernoise.com/drakernoise/blurt/witness-snapshots/latest-blockchain.tar.zst.sha256`
- SHA256:
  - `72a44ab2d0b4112c21a3b1cf17220af4319b48c475f35291ef844ddb2e90817d`

Example restore flow:

```bash
docker pull registry.gitlab.com/blurt/blurt/witness:latest
docker rm -f blurtd || true

cd /var/lib/docker/volumes/blurtd/_data
rm -rf blockchain logs p2p

wget --show-progress -O witness-snapshot.tar.zst <SNAPSHOT_URL>
tar --zstd -xf witness-snapshot.tar.zst

docker run -d \
  --net=host \
  --log-driver=local \
  -v blurtd:/blurtd \
  --name blurtd \
  registry.gitlab.com/blurt/blurt/witness:latest
```

Then restore your own witness configuration.

At minimum, your local setup must provide:

- your own `config.ini`
- your own witness name
- your own private witness signing key
- your own Active key for guarded enable / disable operations
- your own witness URL

Do not copy configuration files from another witness operator.

## Option B: Saboin Presynced Blockchain

If you prefer the upstream presync path, use Saboin's commands.

AMD64:

```bash
wget --show-progress -qO- https://blurt-chain.s3.nl-ams.scw.cloud/witness-0.9.0-amd64-latest.tar.lz4 | lz4 -d | tar x
```

ARM64:

```bash
wget --show-progress -qO- https://blurt-chain.s3.nl-ams.scw.cloud/witness-0.9.0-arm64-latest.tar.lz4 | lz4 -d | tar x
```

Then start the container:

```bash
docker run -d \
  --net=host \
  --log-driver=local \
  -v blurtd:/blurtd \
  --name blurtd \
  registry.gitlab.com/blurt/blurt/witness:latest
```

## Post-Bootstrap Checks

Once the witness is running again:

```bash
docker ps --format '{{.Names}}\t{{.Status}}'
docker logs --tail 50 blurtd
```

You want to see:

- blocks being processed
- no replay loop unless expected
- no config or private key errors

Only then re-enable witness signing.

## Snapshot Publication Rules

If you publish a snapshot for other operators:

- include the exact date
- include a SHA256 file
- publish only sanitized blockchain data
- provide a stable `latest` link if you maintain updates
- document the architecture and BLURT version clearly
- make it explicit that operators must inject their own `config.ini` and witness keys
