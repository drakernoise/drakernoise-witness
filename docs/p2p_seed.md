# P2P Connectivity

For witness and RPC nodes, use multiple healthy peers instead of depending on a single public seed.

## Configuration

Add one or more `p2p-seed-node` lines to your `config.ini`:

```ini
p2p-seed-node = <peer-1>:1776
p2p-seed-node = <peer-2>:1776
```

## Notes

- Do not depend on a single peer for connectivity.
- Prefer a small set of reliable peers operated by different witnesses.
- Keep your P2P surface limited to the hosts that actually need to participate in public peer discovery.
