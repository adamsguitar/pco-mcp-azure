variable "location" {
  type        = string
  description = "Azure region, e.g. eastus"
}

variable "resource_group_name" {
  type        = string
  description = "Resource group name"
}

variable "acr_name" {
  type        = string
  description = "Azure Container Registry name (lowercase, alphanumeric)"
}

variable "containerapps_environment_name" {
  type        = string
  description = "Azure Container Apps environment name"
}

variable "container_app_name" {
  type        = string
  description = "Azure Container App name (used for resource naming)"
}

variable "log_analytics_workspace_name" {
  type        = string
  description = "Log Analytics workspace name"
  default     = null
}
