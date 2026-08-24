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
- `arctura_validator_cycle_latest_seconds`
- `arctura_validator_cycle_max_seconds`
- `arctura_network_emission_tao_per_day`
- `arctura_treasury_emission_tao_per_day`
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

## Optional metagraph emissions snapshot

Issue #6 requires visibility into weight commits and network emissions. Weight
commits come from the evidence journal. Emissions must come from an operator
snapshot after the subnet exists on mainnet.

Use `deploy/monitoring/metagraph-emissions.example.json` as the schema, replace
the placeholder values with observed Finney metagraph/emission data, and place
the reviewed file at:

```text
runs/mainnet-evidence/metagraph-emissions.json
```

`scripts/export_prometheus_metrics.py` appends the emissions metrics when that
file exists. To render only the emissions snapshot:

```bash
python scripts/render_metagraph_emissions.py \
  --snapshot runs/mainnet-evidence/metagraph-emissions.json
```

This path does not query chain state or fabricate emissions. It only renders
operator-provided observations into Prometheus textfile format.

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
- high validator mandate-cycle latency

The repository also includes `deploy/prometheus/prometheus.yml` as a minimal
single-host scrape example for node-exporter:

```bash
prometheus --config.file=deploy/prometheus/prometheus.yml
```

## Compose Monitoring Stack

For a deployable single-host stack, use `deploy/monitoring/docker-compose.yml`.
It runs Prometheus, Alertmanager, node-exporter with the textfile collector, and
Grafana with the Arctura launch dashboard pre-provisioned:

```bash
cd deploy/monitoring
GRAFANA_ADMIN_PASSWORD='replace-this-before-exposure' docker compose up -d
```

The compose stack uses `deploy/monitoring/prometheus.yml`,
`deploy/monitoring/alertmanager.yml`, `deploy/prometheus/arctura-alerts.yml`, and
`deploy/grafana/arctura-launch-dashboard.json`.

For AWS production deployments, `deploy/aws/asg/` includes CloudWatch alarms and
a Lambda bridge that forwards alarm state changes to an Alertmanager-compatible
`/api/v2/alerts` endpoint. This connects EC2 Auto Scaling health signals to the
same Prometheus/Grafana alerting surface used by launch evidence metrics.

To publish the launch evidence report itself into CloudWatch, first render a
safe payload from an existing `arctura-collect-evidence` report:

```bash
python scripts/render_cloudwatch_metrics.py \
  --report runs/mainnet-evidence/report.json \
  --output runs/mainnet-evidence/cloudwatch-metric-data.json
```

The renderer does not call AWS. After operator approval and AWS credentials are
configured, publish the rendered payload explicitly:

```bash
aws cloudwatch put-metric-data \
  --namespace Arctura/Launch \
  --metric-data file://runs/mainnet-evidence/cloudwatch-metric-data.json
```

The payload contains `EvidenceGateOk`, `EvidenceElapsedHours`, `Attestations`,
`HealthPasses`, `WeightCommits`, `MinerRestarts`, `ValidatorRestarts`, and
`FatalMarkers`, each with an `Environment` dimension.

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
- Timeseries: `arctura_validator_cycle_latest_seconds`
- Timeseries: `arctura_network_emission_tao_per_day`
- Timeseries: `arctura_service_restarts_total`

Monitoring does not replace the launch gate. Mainnet remains blocked until
`arctura-collect-evidence` returns `ok: true` and the operator gives explicit
approval for any Finney spend.
