locals {
  log_analytics_workspace_name = coalesce(
    var.log_analytics_workspace_name,
    "law-${var.resource_group_name}"
  )
}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_container_registry" "main" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = local.log_analytics_workspace_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
}

resource "azurerm_container_app_environment" "main" {
  name                = var.containerapps_environment_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

resource "azurerm_user_assigned_identity" "container_app_acr_pull" {
  name                = "${var.container_app_name}-acr-pull"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

resource "azurerm_container_app" "main" {
  name                         = var.container_app_name
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_app_acr_pull.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.container_app_acr_pull.id
  }

  template {
    container {
      name   = "app"
      image  = "acrpcomcpprodeus.azurecr.io/ca-poc-mcp-prod:latest"
      cpu    = 0.5
      memory = "1Gi"
    }
  }

  ingress {
    external_enabled = var.container_app_ingress_external
    target_port      = var.container_app_target_port
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

resource "azurerm_role_assignment" "container_app_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.container_app_acr_pull.principal_id
}
