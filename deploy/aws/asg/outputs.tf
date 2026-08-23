output "miner_autoscaling_group_name" {
  description = "Miner Auto Scaling Group name."
  value       = aws_autoscaling_group.miners.name
}

output "miner_launch_template_id" {
  description = "Miner launch template ID."
  value       = aws_launch_template.miner.id
}

output "alerts_sns_topic_arn" {
  description = "SNS topic receiving CloudWatch alarm state changes."
  value       = aws_sns_topic.alerts.arn
}

output "alarm_bridge_lambda_name" {
  description = "Lambda function that forwards CloudWatch alarms to Alertmanager."
  value       = aws_lambda_function.cloudwatch_to_alertmanager.function_name
}

