output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "acr_name" {
  value = azurerm_container_registry.main.name
}

output "containerapps_environment_name" {
  value = azurerm_container_app_environment.main.name
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.main.name
}

output "user_assigned_identity_id" {
  value       = azurerm_user_assigned_identity.container_app_acr_pull.id
  description = "User-assigned identity ID for Container App ACR pull access"
}

output "user_assigned_identity_client_id" {
  value       = azurerm_user_assigned_identity.container_app_acr_pull.client_id
  description = "Client ID of the user-assigned identity"
}
