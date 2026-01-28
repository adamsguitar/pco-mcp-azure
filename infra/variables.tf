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
  description = "Azure Container App name"
}

variable "container_image_name" {
  type        = string
  description = "Container image name in ACR (repository name without registry prefix)"
}

variable "container_image_tag" {
  type        = string
  description = "Container image tag"
  default     = "latest"
}

variable "container_app_target_port" {
  type        = number
  description = "Container App target port"
  default     = 8080
}

variable "container_app_ingress_external" {
  type        = bool
  description = "Whether to expose the Container App publicly"
  default     = true
}

variable "log_analytics_workspace_name" {
  type        = string
  description = "Log Analytics workspace name"
  default     = null
}
