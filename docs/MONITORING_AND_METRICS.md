# Arctura Base Monitoring and Metrics

Arctura exposes launch-readiness metrics through a Prometheus textfile exporter.
This avoids opening extra HTTP ports on the miner or validator and keeps
monitoring separate from wallet and Bittensor process authority.

## Exporter

Run once:

```bash
python scripts/export_prometheus_metrics.py
```

Default output:

```text
~/.local/share/arctura/metrics/arctura.prom
```

The exporter reads the same systemd services and journals as
`arctura-collect-evidence`, writes the evidence bundle under
`runs/mainnet-evidence`, and atomically writes Prometheus metrics.

Key metrics:

- `arctura_evidence_gate_ok`
- `arctura_evidence_elapsed_hours`
- `arctura_evidence_check_pass{check="duration"}`
- `arctura_attestations_total`
- `arctura_weight_commits_total`
- `arctura_health_passes_total`
- `arctura_service_active{service="arctura-miner"}`
- `arctura_service_restarts_total{service="arctura-validator"}`
- `arctura_fatal_markers_total{marker="Traceback_..."}`

## Systemd Timer

Install the optional timer on the launch host:

```bash
cp deploy/systemd/arctura-metrics.service deploy/systemd/arctura-metrics.timer \
  ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now arctura-metrics.timer
```

Verify:

```bash
systemctl --user status arctura-metrics.timer
systemctl --user start arctura-metrics.service
cat ~/.local/share/arctura/metrics/arctura.prom
```

## Prometheus Integration

Use node-exporter's textfile collector on the host that runs the neurons:

```bash
node_exporter \
  --collector.textfile.directory="$HOME/.local/share/arctura/metrics"
```

Then add or merge `deploy/prometheus/arctura-alerts.yml` into the Prometheus
rule files. The included rules cover:

- exporter failure
- miner or validator service down
- neuron restart during the monitored window
- fatal journal marker
- evidence gate still red after 48 hours
- stale metrics collection
- no weight commit after the initial launch window

The repository also includes `deploy/prometheus/prometheus.yml` as a minimal
single-host scrape example for node-exporter:

```bash
prometheus --config.file=deploy/prometheus/prometheus.yml
```

## Grafana Panels

Import `deploy/grafana/arctura-launch-dashboard.json` into Grafana and point
the `DS_PROMETHEUS` datasource variable at the Prometheus instance that scrapes
node-exporter. The dashboard includes:

- SingleStat: `arctura_evidence_gate_ok`
- Gauge: `arctura_evidence_elapsed_hours`
- Table: `arctura_evidence_check_pass`
- Timeseries: `arctura_health_passes_total`
- Timeseries: `arctura_attestations_total`
- Timeseries: `arctura_weight_commits_total`
- Timeseries: `arctura_service_restarts_total`

Monitoring does not replace the launch gate. Mainnet remains blocked until
`arctura-collect-evidence` returns `ok: true` and the operator gives explicit
approval for any Finney spend.
