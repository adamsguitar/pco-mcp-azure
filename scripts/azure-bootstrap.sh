#!/usr/bin/env bash
set -euo pipefail

# Required inputs
: "${AZURE_SUBSCRIPTION_ID:?Set AZURE_SUBSCRIPTION_ID}"
: "${AZURE_LOCATION:?Set AZURE_LOCATION}"  # e.g. eastus
: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
: "${AZURE_ACR_NAME:?Set AZURE_ACR_NAME}"
: "${AZURE_CONTAINERAPPS_ENVIRONMENT:?Set AZURE_CONTAINERAPPS_ENVIRONMENT}"

# Optional overrides
LOG_ANALYTICS_WORKSPACE_NAME=${LOG_ANALYTICS_WORKSPACE_NAME:-"law-${AZURE_RESOURCE_GROUP}"}

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

# Ensure required resource providers are registered
az provider register --namespace Microsoft.ContainerRegistry --output none
az provider register --namespace Microsoft.App --output none
az provider register --namespace Microsoft.OperationalInsights --output none

# Create resource group
az group create \
  --name "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --output none

# Create ACR
az acr create \
  --name "$AZURE_ACR_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --sku Basic \
  --admin-enabled false \
  --output none

# Create Log Analytics workspace for Container Apps environment
az monitor log-analytics workspace create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$LOG_ANALYTICS_WORKSPACE_NAME" \
  --location "$AZURE_LOCATION" \
  --output none

WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$LOG_ANALYTICS_WORKSPACE_NAME" \
  --query customerId -o tsv)

WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$LOG_ANALYTICS_WORKSPACE_NAME" \
  --query primarySharedKey -o tsv)

# Create Container Apps environment
az containerapp env create \
  --name "$AZURE_CONTAINERAPPS_ENVIRONMENT" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --logs-workspace-id "$WORKSPACE_ID" \
  --logs-workspace-key "$WORKSPACE_KEY" \
  --output none

echo "Bootstrap complete."
