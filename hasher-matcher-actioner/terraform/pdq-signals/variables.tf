# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved

variable "region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "profile" {
  description = "AWS profile to use for authentication"
  type        = string
  default     = null
}

variable "prefix" {
  description = "Prefix to use for resource names"
  type        = string
}

variable "lambda_docker_info" {
  description = "Docker container information for lambda functions"
  type = object({
    uri = string
    commands = object({
      matcher = string
      hasher  = string
      indexer = string
    })
  })
}

variable "datastore" {
  description = "DynamoDB Table to store hash and match information into"
  type = object({
    name = string
    arn  = string
  })
}

variable "images_input" {
  description = "Configuration information for the image content that will be process for PDQ hashes"
  type = object({
    input_queue   = string
    resource_list = list(string)
  })
}

variable "threat_exchange_data" {
  description = "Configuration information for the S3 Bucket that will hold ThreatExchange Data"
  type = object({
    bucket_name        = string
    pdq_file_extension = string
    notification_topic = string
    data_folder        = string
  })
}

variable "index_data_storage" {
  description = "Configuration information for the S3 Bucket that will hold PDQ Index data"
  type = object({
    bucket_name      = string
    index_folder_key = string
  })
}

variable "matches_sns_topic_arn" {
  description = "Output SNS topic to publish new matches to"
  type        = string
}

variable "log_retention_in_days" {
  description = "How long to retain cloudwatch logs for lambda functions in days"
  type        = number
}

variable "additional_tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}

variable "measure_performance" {
  description = "Send metrics to cloudwatch. Useful for benchmarking, but can incur costs. Set to string True for this to work."
  type        = bool
  default     = false
}

variable "metrics_namespace" {
  description = "Cloudwatch namespace for metrics."
  type        = string
  default     = "ThreatExchange/HMA"
}
