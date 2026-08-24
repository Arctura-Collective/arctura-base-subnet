variable "project_name" {
  description = "Project tag and resource-name prefix."
  type        = string
  default     = "arctura-base-subnet"
}

variable "environment" {
  description = "Deployment environment, for example finney-mainnet."
  type        = string
  default     = "finney-mainnet"
}

variable "repo_url" {
  description = "Git repository cloned by instance bootstrap."
  type        = string
  default     = "https://github.com/Arctura-Collective/arctura-base-subnet.git"
}

variable "repo_ref" {
  description = "Git ref deployed on miner instances."
  type        = string
  default     = "main"
}

variable "runtime_user" {
  description = "Linux user that owns the repo checkout and systemd user services."
  type        = string
  default     = "ubuntu"
}

variable "bt_network" {
  description = "Bittensor network name."
  type        = string
  default     = "finney"
}

variable "bt_netuid" {
  description = "Subnet netuid."
  type        = number
}

variable "miner_ami_id" {
  description = "Prebuilt Ubuntu AMI containing runtime prerequisites."
  type        = string
}

variable "miner_instance_type" {
  description = "EC2 instance type for miner nodes."
  type        = string
  default     = "c6i.large"
}

variable "ssh_key_name" {
  description = "Optional EC2 SSH key name."
  type        = string
  default     = null
}

variable "instance_profile_name" {
  description = "IAM instance profile for CloudWatch agent/SSM access."
  type        = string
}

variable "security_group_ids" {
  description = "Security groups attached to miner instances."
  type        = list(string)
}

variable "subnet_ids" {
  description = "Subnet IDs for the miner Auto Scaling Group."
  type        = list(string)
}

variable "root_device_name" {
  description = "Root block-device name for the selected AMI."
  type        = string
  default     = "/dev/sda1"
}

variable "root_volume_size_gb" {
  description = "Encrypted gp3 root volume size."
  type        = number
  default     = 200
}

variable "miner_wallet_name" {
  description = "Hotkey wallet name already present on the AMI or restored by operator-approved bootstrap."
  type        = string
  default     = "arctura_miner"
}

variable "miner_hotkey_name" {
  description = "Miner hotkey name."
  type        = string
  default     = "default"
}

variable "miner_port" {
  description = "Miner axon port."
  type        = number
  default     = 8091
}

variable "miner_min_size" {
  description = "Minimum miner instance count."
  type        = number
  default     = 1
}

variable "miner_max_size" {
  description = "Maximum miner instance count."
  type        = number
  default     = 3
}

variable "miner_desired_capacity" {
  description = "Desired miner instance count."
  type        = number
  default     = 1
}

variable "target_cpu_percent" {
  description = "ASG target-tracking CPU utilization percentage."
  type        = number
  default     = 60
}

variable "high_cpu_alarm_percent" {
  description = "CloudWatch alarm threshold for miner CPU utilization."
  type        = number
  default     = 80
}

variable "high_mandates_per_minute" {
  description = "Custom mandate-load alarm threshold."
  type        = number
  default     = 30
}

variable "alertmanager_webhook_url" {
  description = "Alertmanager /api/v2/alerts endpoint used by the CloudWatch alarm bridge."
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Additional AWS tags."
  type        = map(string)
  default     = {}
}
