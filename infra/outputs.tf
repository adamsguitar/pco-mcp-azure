output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "acr_name" {
  value = azurerm_container_registry.main.name
}

output "containerapps_environment_name" {
  value = azurerm_container_app_environment.main.name
}

output "container_app_name" {
  value = azurerm_container_app.main.name
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.main.name
}
