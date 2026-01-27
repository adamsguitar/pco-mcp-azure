#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_SUBSCRIPTION_ID:?Set AZURE_SUBSCRIPTION_ID}"
: "${AZURE_LOCATION:?Set AZURE_LOCATION}"  # e.g. eastus

TF_STATE_RESOURCE_GROUP=${TF_STATE_RESOURCE_GROUP:-"${AZURE_RESOURCE_GROUP:-}"}
: "${TF_STATE_RESOURCE_GROUP:?Set TF_STATE_RESOURCE_GROUP or AZURE_RESOURCE_GROUP}"

: "${TF_STATE_STORAGE_ACCOUNT:?Set TF_STATE_STORAGE_ACCOUNT}"
: "${TF_STATE_CONTAINER:?Set TF_STATE_CONTAINER}"

az account set --subscription "$AZURE_SUBSCRIPTION_ID"

az provider register --namespace Microsoft.Storage --output none

az group create \
  --name "$TF_STATE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --output none

az storage account create \
  --name "$TF_STATE_STORAGE_ACCOUNT" \
  --resource-group "$TF_STATE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --allow-blob-public-access false \
  --output none

ACCOUNT_KEY=$(az storage account keys list \
  --resource-group "$TF_STATE_RESOURCE_GROUP" \
  --account-name "$TF_STATE_STORAGE_ACCOUNT" \
  --query '[0].value' -o tsv)

az storage container create \
  --name "$TF_STATE_CONTAINER" \
  --account-name "$TF_STATE_STORAGE_ACCOUNT" \
  --account-key "$ACCOUNT_KEY" \
  --output none

echo "Terraform backend bootstrap complete."
