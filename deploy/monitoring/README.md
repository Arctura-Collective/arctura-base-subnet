# Arctura Monitoring Stack

This compose stack is the repository-safe deployment artifact for local or
single-host production monitoring. It does not provision cloud resources.

It runs:

- Prometheus on `:9090`
- Alertmanager on `:9093`
- node-exporter on `:9100` with the textfile collector enabled
- Grafana on `:3000`

## Prerequisites

Install and enable the Arctura metrics timer on the launch host first:

```bash
cp deploy/systemd/arctura-metrics.service deploy/systemd/arctura-metrics.timer \
  ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now arctura-metrics.timer
```

Confirm the textfile exists:

```bash
systemctl --user start arctura-metrics.service
cat ~/.local/share/arctura/metrics/arctura.prom
```

## Start the stack

```bash
cd deploy/monitoring
GRAFANA_ADMIN_PASSWORD='replace-this-before-exposure' docker compose up -d
```

Before exposing this stack outside a private host/network, replace the
placeholder receiver in `alertmanager.yml` with an internal webhook endpoint and
put Grafana/Prometheus/Alertmanager behind authenticated access.

If the textfile collector directory is not the default, set:

```bash
ARCTURA_TEXTFILE_DIR=/path/to/metrics docker compose up -d
```

## Safety boundary

This stack reads Prometheus textfile metrics and sends alert notifications to
the configured Alertmanager webhook only. It does not read wallet mnemonics,
submit weights, register subnets, transfer funds, or mutate AWS.
