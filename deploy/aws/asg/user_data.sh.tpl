#!/usr/bin/env bash
set -euo pipefail

RUNTIME_USER="${runtime_user}"
RUNTIME_HOME="$(getent passwd "$RUNTIME_USER" | cut -d: -f6)"
RUNTIME_UID="$(id -u "$RUNTIME_USER")"
REPO_DIR="/opt/arctura/arctura-base-subnet"

install -d -m 0755 /opt/arctura
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "${repo_url}" "$REPO_DIR"
fi
chown -R "$RUNTIME_USER:$RUNTIME_USER" /opt/arctura

runuser -u "$RUNTIME_USER" -- git -C "$REPO_DIR" fetch --all --tags
runuser -u "$RUNTIME_USER" -- git -C "$REPO_DIR" checkout "${repo_ref}"
runuser -u "$RUNTIME_USER" -- git -C "$REPO_DIR" pull --ff-only || true

runuser -u "$RUNTIME_USER" -- python3 -m venv "$REPO_DIR/.venv"
runuser -u "$RUNTIME_USER" -- "$REPO_DIR/.venv/bin/python" -m pip install --upgrade pip
runuser -u "$RUNTIME_USER" -- "$REPO_DIR/.venv/bin/python" -m pip install -e "$REPO_DIR"

install -d -m 0700 -o "$RUNTIME_USER" -g "$RUNTIME_USER" "$RUNTIME_HOME/.config"
cat > "$RUNTIME_HOME/.config/arctura-base-subnet.env" <<ENV
ARCTURA_REPO=$REPO_DIR
ARCTURA_PYTHON=.venv/bin/python
BT_NETWORK=${bt_network}
BT_NETUID=${bt_netuid}
BT_WALLET_NAME=${miner_wallet_name}
BT_HOTKEY_NAME=${miner_hotkey_name}
BT_MINER_PORT=${miner_port}
ARCTURA_ENERGY_TAG=unknown
ENV
chown "$RUNTIME_USER:$RUNTIME_USER" "$RUNTIME_HOME/.config/arctura-base-subnet.env"
chmod 0600 "$RUNTIME_HOME/.config/arctura-base-subnet.env"

install -d -m 0755 -o "$RUNTIME_USER" -g "$RUNTIME_USER" "$RUNTIME_HOME/.config/systemd/user"
cp "$REPO_DIR/deploy/systemd/arctura-miner.service" \
  "$REPO_DIR/deploy/systemd/arctura-health.service" \
  "$REPO_DIR/deploy/systemd/arctura-health.timer" \
  "$REPO_DIR/deploy/systemd/arctura-metrics.service" \
  "$REPO_DIR/deploy/systemd/arctura-metrics.timer" \
  "$RUNTIME_HOME/.config/systemd/user/"
chown "$RUNTIME_USER:$RUNTIME_USER" "$RUNTIME_HOME/.config/systemd/user"/arctura-*

loginctl enable-linger "$RUNTIME_USER"
runuser -u "$RUNTIME_USER" -- env XDG_RUNTIME_DIR="/run/user/$RUNTIME_UID" systemctl --user daemon-reload
runuser -u "$RUNTIME_USER" -- env XDG_RUNTIME_DIR="/run/user/$RUNTIME_UID" systemctl --user enable --now arctura-miner.service arctura-health.timer arctura-metrics.timer
