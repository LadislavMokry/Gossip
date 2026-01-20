# Server Notes (OnePlace)
Last updated: 2026-01-20

## Hetzner Cloud
- Project: OnePlace
- Server name: oneplace-1
- Location: Nuremberg (eu-central)
- Type: CX23 (2 vCPU / 4 GB RAM / 40 GB SSD)
- OS: Ubuntu 22.04 LTS
- IPv4: 46.224.232.56
- IPv6: 2a01:4f8:1c1f:8f69::1

## Firewall
- Name: oneplace-fw
- Inbound:
  - SSH (TCP 22) from 54.239.6.185/32
  - HTTP (TCP 80) from 0.0.0.0/0 + ::/0
  - HTTPS (TCP 443) from 0.0.0.0/0 + ::/0
  - ICMP from Any IPv4/IPv6 (optional)
- Outbound: default allow

## SSH
- Key name: Am PC
- Key file (local): ~/.ssh/id_ed25519_hetzner
- Login: `ssh -i ~/.ssh/id_ed25519_hetzner root@46.224.232.56`

## Base packages installed
- git
- python3-venv
- python3-pip
- ffmpeg

## Notes
- Update firewall SSH IP if your public IP changes.
- Add additional SSH keys for other computers as needed.
