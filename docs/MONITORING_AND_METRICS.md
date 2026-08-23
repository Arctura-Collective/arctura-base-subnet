# Arctura Base Subnet: Prometheus & Grafana Monitoring Architecture

**Prepared by:** Manus AI (World-Class Bittensor Expert)
**Parent Project:** [Arctura Network](https://arctura.network) | [arctura.network/base](https://arctura.network/base/)
**Repository:** [github.com/Arctura-Collective/arctura-base-subnet](https://github.com/Arctura-Collective/arctura-base-subnet)

---

## 1. Metric Exporter Integration for Bittensor Neurons

Because standard Bittensor neurons use gRPC/Axon transport rather than native HTTP Prometheus endpoints, production monitoring requires embedding `prometheus_client` in `neurons/validator.py` and `neurons/miner.py` to expose a local `/metrics` TCP port (e.g., port `9090` for validators, `9091` for miners).

### Example Exporter Snippet (`arctura_base/metrics.py`)
```python
from prometheus_client import start_http_server, Counter, Histogram, Gauge

# Define core subnet metrics
VALIDATION_LATENCY = Histogram(
    "arctura_validation_latency_seconds", "Time taken to verify miner attestation"
)
VALIDATOR_WEIGHTS_SET = Counter(
    "arctura_validator_weights_set_total", "Total number of successful weight commits"
)
MINER_SUCCESSFUL_PROOFS = Counter(
    "miner_successful_proofs_total", "Total valid Merkle proofs generated"
)
NEURON_UPTIME = Gauge("arctura_neuron_uptime_seconds", "Active uptime of the neuron process")


def init_metrics(port: int):
    start_http_server(port)
    print(f"Prometheus metrics server started on port {port}")
```

---

## 2. Verified Prometheus Alert Rules (`alert.rules.yml`)

```yaml
groups:
  - name: arctura_production_alerts
    rules:
      - alert: NeuronProcessDown
        expr: up{job=~"arctura-.*"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Arctura neuron container down ({{ $labels.job }})"
          description: "The Prometheus scrape target has been unreachable for over 1 minute."

      - alert: HighValidationLatency
        expr: histogram_quantile(0.95, rate(arctura_validation_latency_seconds_bucket[5m])) > 5.0
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "High validation latency on validator node"
          description: "P95 validation latency exceeds 5 seconds."
```

---

## References

- [Bittensor Documentation](https://www.bittensor.com/docs) [11]
- [Prometheus Client Python](https://github.com/prometheus/client_python)
