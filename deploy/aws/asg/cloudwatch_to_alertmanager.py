"""Forward CloudWatch alarm SNS records to Alertmanager's v2 alerts API."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


def _alertmanager_payload(message: dict[str, Any]) -> list[dict[str, Any]]:
    alarm_name = str(message.get("AlarmName", "unknown-cloudwatch-alarm"))
    new_state = str(message.get("NewStateValue", "UNKNOWN"))
    reason = str(message.get("NewStateReason", "No CloudWatch reason provided."))
    region = str(message.get("Region", "unknown"))

    status = "resolved" if new_state == "OK" else "firing"

    return [
        {
            "status": status,
            "labels": {
                "alertname": alarm_name,
                "source": "cloudwatch",
                "region": region,
                "environment": os.environ.get("ARCTURA_ENVIRONMENT", "unknown"),
                "severity": os.environ.get("ALERT_SEVERITY", "critical"),
            },
            "annotations": {
                "summary": alarm_name,
                "description": reason,
            },
            "generatorURL": str(message.get("AlarmArn", "")),
        }
    ]


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    del context

    webhook_url = os.environ["ALERTMANAGER_WEBHOOK_URL"]
    forwarded = 0

    for record in event.get("Records", []):
        sns_message = record.get("Sns", {}).get("Message", "{}")
        message = json.loads(sns_message)
        payload = json.dumps(_alertmanager_payload(message)).encode("utf-8")
        request = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status >= 300:
                raise RuntimeError(f"Alertmanager webhook returned HTTP {response.status}")
        forwarded += 1

    return {"forwarded": forwarded}
