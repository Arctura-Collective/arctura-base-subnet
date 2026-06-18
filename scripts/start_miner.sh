#!/usr/bin/env bash
# scripts/start_miner.sh
set -euo pipefail
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
NETWORK="${NETWORK:-${BT_NETWORK:-test}}"
NETUID="${NETUID:-${BT_NETUID:-1}}"
WALLET="${WALLET:-${BT_MINER_WALLET:-miner}}"
HOTKEY="${HOTKEY:-${BT_DEFAULT_HOTKEY:-default}}"
PORT="${MINER_AXON_PORT:-8091}"
while [[ $# -gt 0 ]]; do
  case $1 in
    --network) NETWORK="$2"; shift 2;;
    --netuid)  NETUID="$2";  shift 2;;
    --wallet)  WALLET="$2";  shift 2;;
    *) echo "Unknown: $1"; exit 1;;
  esac
done
echo "Starting Arctura Base miner | network=${NETWORK} netuid=${NETUID}"
python neurons/miner.py \
  --wallet.name "${WALLET}" \
  --wallet.hotkey "${HOTKEY}" \
  --subtensor.network "${NETWORK}" \
  --netuid "${NETUID}" \
  --axon.port "${PORT}" \
  --logging.info
