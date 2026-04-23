# P2P Seed Node

Add our seed node to your witness configuration to improve network connectivity and block propagation.

## Configuration

Add the following line to your `config.ini` file:

```ini
p2p-seed-node = 136.243.80.162:1776
```

## Node Specs

- **Location**: Germany (Hetzner)
- **Bandwidth**: 1Gbps Uplink
- **Role**: Public BLURT seed for peer discovery

## Notes

- Treat this as a convenience seed, not as the only peer in your witness config.
- Keep multiple healthy peers in your setup.
