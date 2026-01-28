# Migration Guide: Option A Implementation

## Overview

This migration implements **Option A: Terraform for Infrastructure Only**, which separates infrastructure management from application deployment to eliminate the chicken-and-egg problem and state drift issues.

## Changes Made

### 1. Terraform Configuration

#### [infra/main.tf](infra/main.tf)
- **REMOVED**: `azurerm_container_app.main` resource (lines 42-78)
- **KEPT**: All infrastructure resources:
  - Resource Group
  - Container Registry (ACR)
  - Log Analytics Workspace
  - Container Apps Environment
  - User-Assigned Identity for ACR pull
  - Role Assignment (AcrPull permission)

**Why**: Terraform now manages only the underlying infrastructure, not the Container App itself. This prevents conflicts with the deployment action.

#### [infra/variables.tf](infra/variables.tf)
- **REMOVED**: Container image-related variables:
  - `container_image_name`
  - `container_image_tag`
  - `container_app_target_port`
  - `container_app_ingress_external`
- **KEPT**: `container_app_name` (used for identity naming)

**Why**: These variables are no longer needed by Terraform since it doesn't manage the Container App.

#### [infra/outputs.tf](infra/outputs.tf)
- **REMOVED**: `output "container_app_name"` (no longer managed by Terraform)
- **ADDED**:
  - `output "user_assigned_identity_id"` - Full resource ID of the identity
  - `output "user_assigned_identity_client_id"` - Client ID for registry authentication

**Why**: These outputs help the deployment workflow authenticate to ACR using the managed identity.

#### [infra/terraform.tfvars](infra/terraform.tfvars)
- **REMOVED**: `container_image_name` and `container_image_tag` variables
- **KEPT**: All infrastructure configuration

**Why**: These aren't Terraform variables anymore, so they can't be in terraform.tfvars.

---

### 2. Deployment Configuration

#### [deployment-config.env](deployment-config.env) - **NEW FILE**
```bash
container_image_name="pco-mcp"
container_image_tag="latest"
```

**Why**: Image configuration is now separate from Terraform. The GitHub Actions workflow reads this file to determine what Docker image to build and deploy.

---

### 3. GitHub Actions Workflow

#### [.github/workflows/azure-containerapp.yml](.github/workflows/azure-containerapp.yml)

**Changed: "Resolve image settings" step** (lines 27-42)
- Now reads from `deployment-config.env` instead of `infra/terraform.tfvars`

**REMOVED: "Terraform Import Existing" step** (was lines 80-88)
- **This was an anti-pattern** - running imports on every deployment is unnecessary
- Import is a one-time operation for migrating existing resources
- Once resources are in Terraform state (stored in Azure Storage), they stay there
- Removed to improve performance and reduce risk of state corruption
- Created separate manual workflow for one-time imports: `terraform-import-existing.yml`

**Added: "Terraform Plan" step** (new, before apply)
- Runs `terraform plan -out=tfplan` to preview changes
- Helps catch errors before apply
- No longer passes image-related variables (they're not needed)

**Changed: "Terraform Apply" step** (lines 106-122)
- Now uses the plan file: `terraform apply -auto-approve tfplan`
- Removed image-related environment variables: `TF_VAR_container_image_name`, `TF_VAR_container_image_tag`
- Only manages infrastructure now

**Added: "Get User-Assigned Identity Client ID" step** (lines 126-134)
- Retrieves the client ID of the managed identity created by Terraform
- Needed for the Container App to authenticate to ACR

**Changed: "Build and deploy Container App" step** (lines 136-192)
- Replaced the `azure/container-apps-deploy-action@v2` with native `az containerapp` commands
- Uses bash script with proper error handling
- **Creates Container App** if it doesn't exist (with all configuration)
- **Updates Container App** if it exists (image + secrets)
- Stores secrets using Container App secrets (not environment variables)
- References secrets via `secretref:` in environment variables
- Uses the managed identity for ACR authentication

**Why**:
- The Azure action v2 had issues with `envVars` parameter
- Native Azure CLI gives more control over create vs. update logic
- Secrets are now properly stored in Container App secrets (encrypted at rest)
- The workflow intelligently handles both initial deployment and updates

---

### 4. Import Script and One-Time Migration Workflow

#### [scripts/tf-import-existing.sh](scripts/tf-import-existing.sh)
- **ADDED**: Import logic for `azurerm_user_assigned_identity.container_app_acr_pull`
- **ADDED**: Import logic for `azurerm_role_assignment.container_app_acr_pull`
- **REMOVED**: Import logic for `azurerm_container_app.main` (no longer managed)

**Why**: These resources were defined in Terraform but weren't being imported, causing "already exists" errors on re-runs.

#### [.github/workflows/terraform-import-existing.yml](.github/workflows/terraform-import-existing.yml) - **NEW FILE**

A separate manual workflow for one-time resource imports. This workflow:
- Only runs when manually triggered (`workflow_dispatch`)
- Requires typing "import" to confirm (safety mechanism)
- Shows Terraform state before and after import
- Verifies the plan after import to ensure correctness
- Should only be used for:
  - Initial migration of existing infrastructure to Terraform
  - Adding new Terraform resources that already exist in Azure
  - State recovery (use with caution)

**Why Create This**:
- Running imports on every deployment was an anti-pattern
- Import is a one-time operation, not part of regular deployment
- Separating concerns: deployment workflow vs. setup/migration workflow
- Better performance and reduced risk of state corruption

---

## New Deployment Flow

### Previous Flow (Problematic)
```
1. Resolve image settings
2. Bootstrap Terraform backend
3. Terraform Init
4. Terraform Import
5. Login to ACR
6. Build and push image        ← Image created
7. Terraform Apply              ← Tries to create Container App with image (FAILS)
8. Azure Container Apps action  ← Re-deploys (conflicts with Terraform)
```

### New Flow (Fixed)
```
1. Resolve image settings
2. Bootstrap Terraform backend
3. Terraform Init
4. Terraform Import
5. Terraform Plan               ← Preview infrastructure changes
6. Terraform Apply              ← Creates/updates ONLY infrastructure
7. Login to ACR
8. Build and push image         ← Image created and pushed to ACR
9. Get Identity Client ID       ← Retrieve identity for ACR auth
10. Deploy Container App        ← Creates/updates Container App with image + secrets
```

**Key Differences:**
- Terraform runs BEFORE image build (but doesn't create Container App)
- Image build happens BEFORE Container App deployment
- Container App deployment is SEPARATE from Terraform
- No conflicts or state drift

---

## How to Deploy

### First-Time Deployment (Clean Slate)

If you're deploying to a fresh Azure subscription or want to start clean:

```bash
# 1. Commit the changes
git add .
git commit -m "Implement Option A: Separate infrastructure from deployment"
git push origin main

# 2. GitHub Actions will automatically:
#    - Create all infrastructure via Terraform
#    - Build and push Docker image
#    - Deploy Container App with secrets
```

### Migrating Existing Deployment

If you already have resources deployed from the old configuration, you have two options:

**Option 1: One-Time Import (Recommended for First Migration)**

If this is your very first time running the new workflow and you have existing infrastructure:

```bash
# 1. Push the code changes first
git push origin main

# 2. Go to GitHub Actions → "Terraform Import Existing Resources" workflow
# 3. Click "Run workflow"
# 4. Type "import" in the confirmation field
# 5. Click "Run workflow" button

# This will import all existing resources into Terraform state
# You only need to do this ONCE
```

After the import completes, review the Terraform plan output. If it shows no changes (or only minor ones), you're good! The regular deployment workflow will now work correctly.

**Option 2: Let Terraform Create Resources (Clean Slate)**

If you want to start fresh OR if your existing resources are in a failed state:

```bash
# 1. Delete the failed/old Container App (if it exists)
az containerapp delete --name ca-pco-mcp-prod --resource-group rg-pco-mcp-prod-eastus --yes

# 2. Remove Container App from Terraform state (if it's there)
cd infra
terraform state rm azurerm_container_app.main  # This will fail if not in state - that's OK

# 3. Push the changes
git push origin main

# The workflow will create everything fresh
```

**Option 3: Manual State Cleanup (If Options 1-2 Don't Work)**

```bash
# Remove the Container App from state since we're no longer managing it with Terraform
cd infra
terraform state rm azurerm_container_app.main

# Push and let the workflow handle it
git push origin main
```

---

## What to Expect

### During First Run
1. Terraform will create/update infrastructure resources
2. If Container App already exists, it will be updated by the workflow
3. Secrets will be created/updated in the Container App
4. A new revision will be deployed with the latest image

### During Subsequent Runs
1. Terraform will only update infrastructure if you change those resources
2. Docker image will be built and pushed with the tag from `deployment-config.env`
3. Container App will be updated with the new image
4. Secrets are refreshed on every deployment (ensuring they're current)

---

## Verifying the Deployment

After the workflow completes:

```bash
# 1. Check Container App status
az containerapp show \
  --name ca-pco-mcp-prod \
  --resource-group rg-pco-mcp-prod-eastus \
  --query "{name:name, status:properties.runningStatus, fqdn:properties.configuration.ingress.fqdn}"

# 2. Check secrets are configured
az containerapp secret list \
  --name ca-pco-mcp-prod \
  --resource-group rg-pco-mcp-prod-eastus

# 3. Check environment variables reference secrets
az containerapp show \
  --name ca-pco-mcp-prod \
  --resource-group rg-pco-mcp-prod-eastus \
  --query "properties.template.containers[0].env"

# 4. Test the MCP server endpoint
curl https://$(az containerapp show \
  --name ca-pco-mcp-prod \
  --resource-group rg-pco-mcp-prod-eastus \
  --query "properties.configuration.ingress.fqdn" -o tsv)/

# 5. Check logs
az containerapp logs show \
  --name ca-pco-mcp-prod \
  --resource-group rg-pco-mcp-prod-eastus \
  --follow
```

---

## Rollback Plan

If something goes wrong and you need to revert:

```bash
# 1. Revert the Git commit
git revert HEAD
git push origin main

# OR restore to previous commit
git reset --hard <previous-commit-sha>
git push --force origin main

# 2. Manually fix Container App if needed
az containerapp update \
  --name ca-pco-mcp-prod \
  --resource-group rg-pco-mcp-prod-eastus \
  --image acrpcomcpprodeus.azurecr.io/pco-mcp:latest
```

---

## Future Improvements

### Consider Using Git Commit SHA for Image Tags
Instead of always using "latest", use the Git commit SHA:

**Update [deployment-config.env](deployment-config.env):**
```bash
container_image_name="pco-mcp"
container_image_tag="${GITHUB_SHA:0:7}"  # First 7 chars of commit hash
```

**Update workflow to substitute:**
```bash
image_tag=$(awk -F'=' '/^container_image_tag/ {gsub(/["[:space:]]/, "", $2); print $2}' "$config_file")
image_tag="${image_tag//\$\{GITHUB_SHA:0:7\}/${GITHUB_SHA:0:7}}"
```

**Benefits:**
- Each deployment has a unique, traceable image tag
- Easy rollbacks (just deploy a previous commit's image)
- Better audit trail

### Add Health Checks
Add to the Container App deployment:
```bash
--health-probe-interval 30 \
--health-probe-timeout 5 \
--health-probe-path /health
```

### Add Resource Limits
Consider adding min/max replica configuration based on load:
```bash
--min-replicas 1 \  # Always have 1 instance running
--max-replicas 5 \  # Scale up to 5 under load
```

---

## Troubleshooting

### "Identity not found" error
**Cause**: Terraform hasn't created the identity yet or it failed to create.

**Fix**:
```bash
# Check if identity exists
az identity show \
  --name ca-pco-mcp-prod-acr-pull \
  --resource-group rg-pco-mcp-prod-eastus

# If not, run Terraform manually
cd infra
terraform apply
```

### "Image not found in ACR" error
**Cause**: Image build/push failed before Container App deployment.

**Fix**: Check the "Build and push image to ACR" step logs in GitHub Actions.

### "Secret not found" error
**Cause**: GitHub secrets `PCO_APPLICATION_ID` or `PCO_SECRET_KEY` are not configured.

**Fix**:
```bash
# Verify secrets are set in GitHub
# Go to: Settings > Secrets and variables > Actions
# Ensure both secrets exist and have values
```

### Terraform state drift warnings
**Cause**: This is normal now - Container App is managed outside Terraform.

**Fix**: Ignore warnings about `azurerm_container_app.main` not being in state. That's intentional.

---

## Summary

This migration successfully:
- ✅ Eliminates the chicken-and-egg problem (image built before Container App deployment)
- ✅ Removes duplicate deployments and state drift
- ✅ Properly stores secrets in Container App secrets (encrypted)
- ✅ Adds Terraform plan step for safety
- ✅ Improves import script to cover all resources
- ✅ Uses managed identity for secure ACR authentication
- ✅ Separates concerns: Terraform = infrastructure, Azure CLI = application deployment

Your deployments should now be reliable and consistent! 🎉
