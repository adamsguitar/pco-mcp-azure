#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_SUBSCRIPTION_ID:?Set AZURE_SUBSCRIPTION_ID}"
: "${TF_VAR_location:?Set TF_VAR_location}"
: "${TF_VAR_resource_group_name:?Set TF_VAR_resource_group_name}"
: "${TF_VAR_acr_name:?Set TF_VAR_acr_name}"
: "${TF_VAR_containerapps_environment_name:?Set TF_VAR_containerapps_environment_name}"
: "${TF_VAR_container_app_name:?Set TF_VAR_container_app_name}"

LOG_ANALYTICS_WORKSPACE_NAME=${TF_VAR_log_analytics_workspace_name:-"law-${TF_VAR_resource_group_name}"}

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

ensure_import() {
  local tf_addr="$1"
  local az_id="$2"

  if terraform state list | grep -q "^${tf_addr}$"; then
    echo "Already in state: ${tf_addr}"
    return 0
  fi

  if [[ -z "$az_id" ]]; then
    echo "Not found in Azure: ${tf_addr}"
    return 0
  fi

  echo "Importing ${tf_addr}"
  terraform import "$tf_addr" "$az_id"
}

rg_id=$(az group show --name "$TF_VAR_resource_group_name" --query id -o tsv 2>/dev/null || true)
acr_id=$(az acr show --name "$TF_VAR_acr_name" --resource-group "$TF_VAR_resource_group_name" --query id -o tsv 2>/dev/null || true)
log_id=$(az monitor log-analytics workspace show --resource-group "$TF_VAR_resource_group_name" --workspace-name "$LOG_ANALYTICS_WORKSPACE_NAME" --query id -o tsv 2>/dev/null || true)
cae_id=$(az containerapp env show --name "$TF_VAR_containerapps_environment_name" --resource-group "$TF_VAR_resource_group_name" --query id -o tsv 2>/dev/null || true)
ca_id=$(az containerapp show --name "$TF_VAR_container_app_name" --resource-group "$TF_VAR_resource_group_name" --query id -o tsv 2>/dev/null || true)

ensure_import azurerm_resource_group.main "$rg_id"
ensure_import azurerm_container_registry.main "$acr_id"
ensure_import azurerm_log_analytics_workspace.main "$log_id"
ensure_import azurerm_container_app_environment.main "$cae_id"
ensure_import azurerm_container_app.main "$ca_id"

