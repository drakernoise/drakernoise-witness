# Witness Bootstrap Guide

This guide describes a practical witness bootstrap and upgrade flow using:

- the guarded enable / disable helpers in this repository
- a compatible presynced blockchain source
- either the published sanitized snapshot or another equivalent presync archive

## Before You Start

You need:

- Docker installed on the witness host
- `lz4` installed if your presync source uses `.tar.lz4`
- `zstd` support if your snapshot uses `.tar.zst`
- your own witness configuration values
- your own witness Active key available only on the server

Important:

- never publish your witness `config.ini`
- never publish your Active key
- never publish a snapshot that contains `config.ini`, `wallet.json`, or other secrets

## Guarded Witness Toggle

This repository includes safer witness toggle helpers:

- [`scripts/witness_guard.py`](../scripts/witness_guard.py)
- [`scripts/secrets.env.example`](../scripts/secrets.env.example)

Prepare a local secrets file:

```bash
cp scripts/secrets.env.example scripts/.secrets.env
chmod 600 scripts/.secrets.env
```

Then edit it with your own values.

Before any upgrade, replay or bootstrap operation:

```bash
cd scripts
python3 witness_guard.py disable
```

After the node is back and stable:

```bash
cd scripts
python3 witness_guard.py enable
```

If autodetection does not find your witness container, either set `BLURT_WITNESS_CONTAINER` or pass `--container-name <name>` explicitly.

The standalone `check` subcommand is optional. It is useful for diagnostics, but `witness_guard.py disable` and `witness_guard.py enable` already enforce the safe-window check internally.

## Recommended Bootstrap Flow

The stable pattern is:

1. Disable the witness first.
2. Pull the target witness image.
3. Remove the old container.
4. Replace the local blockchain with a compatible presynced source.
5. Start the witness again.
6. Re-enable the witness only after the node is healthy.

The only thing that changes between environments is the source of the presynced data.

## Presync Source Requirements

Use only a source that contains blockchain data and no secrets.

Expected contents:

- `blurt-witness-data/blockchain/`

Do not use a snapshot if it contains:

- `config.ini`
- `wallet.json`
- `logs/`
- `p2p/`

Whether you use the published snapshot from this repo or another compatible archive, the restore flow is the same:

1. stop and remove the old container
2. clear the local blockchain data
3. extract the presynced data into the witness volume or data dir
4. start the witness again
5. restore your own witness configuration
6. re-enable signing only after health checks pass

## Snapshot Download

Use the latest published snapshot:

- snapshot:
  - `https://images.drakernoise.com/drakernoise/blurt/witness-snapshots/latest-blockchain.tar.zst`
- checksum:
  - `https://images.drakernoise.com/drakernoise/blurt/witness-snapshots/latest-blockchain.tar.zst.sha256`

Example restore flow with a `.tar.zst` snapshot:

```bash
docker pull registry.gitlab.com/blurt/blurt/witness:latest
docker rm -f blurtd || true
docker volume create blurtd >/dev/null

BLURTD_MOUNT=$(docker volume inspect blurtd --format '{{.Mountpoint}}')
rm -rf "$BLURTD_MOUNT/blockchain" "$BLURTD_MOUNT/logs" "$BLURTD_MOUNT/p2p"

wget --show-progress -O witness-snapshot.tar.zst <SNAPSHOT_URL>
tar --zstd -xf witness-snapshot.tar.zst -C "$BLURTD_MOUNT"

docker run -d \
  --net=host \
  --log-driver=local \
  -v blurtd:/blurtd \
  --name blurtd \
  registry.gitlab.com/blurt/blurt/witness:latest
```

## Example Presync Archive With `.lz4`

If your chosen presync source publishes `.tar.lz4`, extract it like this.

AMD64:

```bash
wget --show-progress -qO- https://blurt-chain.s3.nl-ams.scw.cloud/witness-0.9.0-amd64-latest.tar.lz4 | lz4 -d | tar x
```

ARM64:

```bash
wget --show-progress -qO- https://blurt-chain.s3.nl-ams.scw.cloud/witness-0.9.0-arm64-latest.tar.lz4 | lz4 -d | tar x
```

Example restore flow with a `.tar.lz4` presync archive:

```bash
docker pull registry.gitlab.com/blurt/blurt/witness:latest
docker rm -f blurtd || true
docker volume create blurtd >/dev/null

BLURTD_MOUNT=$(docker volume inspect blurtd --format '{{.Mountpoint}}')
rm -rf "$BLURTD_MOUNT/blockchain" "$BLURTD_MOUNT/logs" "$BLURTD_MOUNT/p2p"

wget --show-progress -qO- <PRESYNC_URL> | lz4 -d | tar x -C "$BLURTD_MOUNT"

docker run -d \
  --net=host \
  --log-driver=local \
  -v blurtd:/blurtd \
  --name blurtd \
  registry.gitlab.com/blurt/blurt/witness:latest
```

## Local Configuration

After restoring blockchain data, your own local setup must provide:

- your own `config.ini`
- your own witness name
- your own private witness signing key
- your own Active key for guarded enable / disable operations
- your own witness URL

Do not copy configuration files from another operator.

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

## Publication Rules

If you publish a snapshot for other operators:

- include the exact date
- include a SHA256 file
- publish only sanitized blockchain data
- provide a stable `latest` link if you maintain updates
- document the architecture and BLURT version clearly
- make it explicit that operators must inject their own `config.ini` and witness keys
