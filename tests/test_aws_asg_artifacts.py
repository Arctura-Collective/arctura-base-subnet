"""Static checks for AWS Auto Scaling and CloudWatch alerting artifacts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AWS_ASG = ROOT / "deploy" / "aws" / "asg"


def test_aws_asg_module_contains_miner_autoscaling_resources():
    main_tf = (AWS_ASG / "main.tf").read_text(encoding="utf-8")
    variables_tf = (AWS_ASG / "variables.tf").read_text(encoding="utf-8")
    tfvars = (AWS_ASG / "terraform.tfvars.example").read_text(encoding="utf-8")

    assert 'resource "aws_launch_template" "miner"' in main_tf
    assert 'resource "aws_autoscaling_group" "miners"' in main_tf
    assert 'health_check_type         = "EC2"' in main_tf
    assert 'volume_type           = "gp3"' in main_tf
    assert "encrypted             = true" in main_tf
    assert 'variable "root_volume_size_gb"' in variables_tf
    assert "default     = 200" in variables_tf
    assert "root_volume_size_gb     = 200" in tfvars
    assert 'resource "aws_autoscaling_policy" "miner_cpu_target"' in main_tf
    assert 'policy_type            = "TargetTrackingScaling"' in main_tf
    assert 'resource "aws_autoscaling_policy" "miner_mandate_step_out"' in main_tf
    assert "MandatesPerMinute" in main_tf


def test_aws_asg_module_contains_cloudwatch_to_prometheus_alert_bridge():
    main_tf = (AWS_ASG / "main.tf").read_text(encoding="utf-8")
    bridge = (AWS_ASG / "cloudwatch_to_alertmanager.py").read_text(encoding="utf-8")

    assert 'resource "aws_cloudwatch_metric_alarm" "miner_high_cpu"' in main_tf
    assert 'resource "aws_cloudwatch_metric_alarm" "miner_high_mandate_load"' in main_tf
    assert 'resource "aws_cloudwatch_metric_alarm" "miner_unhealthy_capacity"' in main_tf
    assert 'resource "aws_cloudwatch_metric_alarm" "validator_health_failures"' in main_tf
    assert 'resource "aws_sns_topic" "alerts"' in main_tf
    assert 'resource "aws_lambda_function" "cloudwatch_to_alertmanager"' in main_tf
    assert "ALERTMANAGER_WEBHOOK_URL" in main_tf
    assert "/api/v2/alerts" in (AWS_ASG / "terraform.tfvars.example").read_text(encoding="utf-8")
    assert '"source": "cloudwatch"' in bridge
    assert "urllib.request.Request" in bridge


def test_aws_asg_user_data_starts_miner_health_and_metrics_only():
    user_data = (AWS_ASG / "user_data.sh.tpl").read_text(encoding="utf-8")

    assert 'RUNTIME_USER="${runtime_user}"' in user_data
    assert "loginctl enable-linger" in user_data
    assert "systemctl --user enable --now arctura-miner.service" in user_data
    assert "arctura-miner.service" in user_data
    assert "arctura-health.timer" in user_data
    assert "arctura-metrics.timer" in user_data
    assert "arctura-validator.service" not in user_data
    assert "coldkey" not in user_data.lower()


def test_aws_asg_readme_sets_safe_deployment_boundary():
    readme = (AWS_ASG / "README.md").read_text(encoding="utf-8")

    lower_readme = readme.lower()

    assert "never" in lower_readme
    assert "provisions aws resources" in lower_readme
    assert "Do not place coldkeys" in readme
    assert "CloudWatch" in readme
    assert "Auto Scaling Group" in readme
    assert "Alertmanager" in readme
    assert "arctura-aws-asg-audit" in readme
    assert "arctura-validator-failover-plan" in readme
    assert "never stops a" in readme


def test_validator_failover_probe_template_is_non_executing():
    template = (AWS_ASG / "validator-probe.example.json").read_text(encoding="utf-8")

    assert "primary_validator" in template
    assert "standby_validator" in template
    assert "operator_approved" in template


def test_aws_asg_artifact_is_linked_from_launch_and_monitoring_docs():
    launch = (ROOT / "docs" / "FINNEY_MAINNET_LAUNCH_STRATEGY.md").read_text(encoding="utf-8")
    monitoring = (ROOT / "docs" / "MONITORING_AND_METRICS.md").read_text(encoding="utf-8")

    assert "deploy/aws/asg/" in launch
    assert "Auto Scaling Group" in launch
    assert "CloudWatch-to-Alertmanager" in launch
    assert "deploy/aws/asg/" in monitoring
    assert "/api/v2/alerts" in monitoring
