terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Component   = "arctura-base-subnet"
    },
    var.tags,
  )
}

data "archive_file" "cloudwatch_to_alertmanager" {
  type        = "zip"
  source_file = "${path.module}/cloudwatch_to_alertmanager.py"
  output_path = "${path.module}/build/cloudwatch_to_alertmanager.zip"
}

resource "aws_iam_role" "alarm_bridge" {
  name = "${local.name_prefix}-alarm-bridge"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "alarm_bridge_basic" {
  role       = aws_iam_role.alarm_bridge.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "cloudwatch_to_alertmanager" {
  function_name    = "${local.name_prefix}-cloudwatch-to-alertmanager"
  role             = aws_iam_role.alarm_bridge.arn
  filename         = data.archive_file.cloudwatch_to_alertmanager.output_path
  source_code_hash = data.archive_file.cloudwatch_to_alertmanager.output_base64sha256
  handler          = "cloudwatch_to_alertmanager.lambda_handler"
  runtime          = "python3.12"
  timeout          = 10

  environment {
    variables = {
      ALERTMANAGER_WEBHOOK_URL = var.alertmanager_webhook_url
      ALERT_SEVERITY           = "critical"
      ARCTURA_ENVIRONMENT      = var.environment
    }
  }

  tags = local.common_tags
}

resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "alarm_bridge" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.cloudwatch_to_alertmanager.arn
}

resource "aws_lambda_permission" "allow_sns_alarm_bridge" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cloudwatch_to_alertmanager.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.alerts.arn
}

resource "aws_launch_template" "miner" {
  name_prefix   = "${local.name_prefix}-miner-"
  image_id      = var.miner_ami_id
  instance_type = var.miner_instance_type
  key_name      = var.ssh_key_name

  vpc_security_group_ids = var.security_group_ids

  iam_instance_profile {
    name = var.instance_profile_name
  }

  monitoring {
    enabled = true
  }

  block_device_mappings {
    device_name = var.root_device_name

    ebs {
      volume_size           = var.root_volume_size_gb
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh.tpl", {
    runtime_user      = var.runtime_user
    repo_url          = var.repo_url
    repo_ref          = var.repo_ref
    bt_network        = var.bt_network
    bt_netuid         = var.bt_netuid
    miner_wallet_name = var.miner_wallet_name
    miner_hotkey_name = var.miner_hotkey_name
    miner_port        = var.miner_port
  }))

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "${local.name_prefix}-miner"
      Role = "miner"
    })
  }

  tags = local.common_tags
}

resource "aws_autoscaling_group" "miners" {
  name                      = "${local.name_prefix}-miners"
  min_size                  = var.miner_min_size
  max_size                  = var.miner_max_size
  desired_capacity          = var.miner_desired_capacity
  vpc_zone_identifier       = var.subnet_ids
  health_check_type         = "EC2"
  health_check_grace_period = 300

  launch_template {
    id      = aws_launch_template.miner.id
    version = "$Latest"
  }

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 100
    }
  }

  dynamic "tag" {
    for_each = merge(local.common_tags, {
      Name = "${local.name_prefix}-miner"
      Role = "miner"
    })

    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
}

resource "aws_autoscaling_policy" "miner_cpu_target" {
  name                   = "${local.name_prefix}-miner-cpu-target"
  autoscaling_group_name = aws_autoscaling_group.miners.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }

    target_value = var.target_cpu_percent
  }
}

resource "aws_autoscaling_policy" "miner_mandate_step_out" {
  name                   = "${local.name_prefix}-miner-mandate-step-out"
  autoscaling_group_name = aws_autoscaling_group.miners.name
  policy_type            = "StepScaling"
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300

  step_adjustment {
    metric_interval_lower_bound = 0
    scaling_adjustment          = 1
  }
}

resource "aws_cloudwatch_metric_alarm" "miner_high_cpu" {
  alarm_name          = "${local.name_prefix}-miner-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = var.high_cpu_alarm_percent
  alarm_description   = "Miner CPU exceeded launch-readiness threshold."
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.miners.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "miner_high_mandate_load" {
  alarm_name          = "${local.name_prefix}-miner-high-mandate-load"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MandatesPerMinute"
  namespace           = "Arctura/Miner"
  period              = 60
  statistic           = "Average"
  threshold           = var.high_mandates_per_minute
  alarm_description   = "Miner mandate load exceeded scaling threshold."
  alarm_actions       = [aws_autoscaling_policy.miner_mandate_step_out.arn, aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    Environment = var.environment
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "miner_unhealthy_capacity" {
  alarm_name          = "${local.name_prefix}-miner-unhealthy-capacity"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "GroupInServiceInstances"
  namespace           = "AWS/AutoScaling"
  period              = 60
  statistic           = "Average"
  threshold           = var.miner_min_size
  alarm_description   = "Miner ASG has fewer in-service instances than the configured minimum."
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.miners.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "validator_health_failures" {
  alarm_name          = "${local.name_prefix}-validator-health-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ValidatorHealthFailures"
  namespace           = "Arctura/Validator"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_description   = "Validator health probe reported one or more failures."
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    Environment = var.environment
  }

  tags = local.common_tags
}
