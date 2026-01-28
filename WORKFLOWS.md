# GitHub Actions Workflows Guide

This project has two GitHub Actions workflows with different purposes.

## 1. Deploy to Azure Container Apps (Main Workflow)

**File**: [.github/workflows/azure-containerapp.yml](.github/workflows/azure-containerapp.yml)

**Purpose**: Regular deployment of the application to Azure

**When it runs**:
- Automatically on every push to `main` branch
- Manually via "Run workflow" button

**What it does**:
1. Builds and pushes Docker image to ACR
2. Applies Terraform to manage infrastructure (ACR, environment, identity, permissions)
3. Deploys Container App with the new image and secrets

**Use this for**:
- Deploying code changes
- Updating the application
- Normal day-to-day operations

**Frequency**: Runs on every push to main (continuous deployment)

---

## 2. Terraform Import Existing Resources (Setup Workflow)

**File**: [.github/workflows/terraform-import-existing.yml](.github/workflows/terraform-import-existing.yml)

**Purpose**: One-time migration of existing Azure resources into Terraform state

**When it runs**:
- **ONLY** when manually triggered
- Requires typing "import" to confirm

**What it does**:
1. Imports existing Azure resources into Terraform state
2. Shows before/after state comparison
3. Runs Terraform plan to verify correctness

**Use this for**:
- **First-time setup**: Migrating existing infrastructure to Terraform management
- **Adding new resources**: When you add new Terraform resources that already exist in Azure
- **State recovery**: Recovering from Terraform state corruption (rare, use with caution)

**Frequency**: **ONE TIME ONLY** (or very rarely for recovery)

**⚠️ Important**: Do NOT run this workflow repeatedly. Once resources are imported into Terraform state, they stay there (state is stored in Azure Storage). Running import multiple times is unnecessary and can cause issues.

---

## When to Use Which Workflow

### Scenario: First Time Setting Up This Project

1. ✅ Run **"Terraform Import Existing Resources"** if you have existing Azure resources
2. ✅ Then use **"Deploy to Azure Container Apps"** for all future deployments

### Scenario: Deploying Code Changes

✅ Use **"Deploy to Azure Container Apps"** (automatic on push to main)

### Scenario: Updating Infrastructure (Terraform Changes)

✅ Use **"Deploy to Azure Container Apps"** (automatic on push to main)

### Scenario: Adding a New Azure Resource to Terraform Config That Already Exists

1. ✅ Run **"Terraform Import Existing Resources"** once
2. ✅ Then use **"Deploy to Azure Container Apps"** normally

### Scenario: Terraform State Got Corrupted

1. ⚠️ Investigate what went wrong first
2. ⚠️ Consider restoring from Azure Storage backup if available
3. ⚠️ As last resort, run **"Terraform Import Existing Resources"**

---

## Why We Separated These Workflows

### The Problem (Before)

The deployment workflow used to run `terraform import` on **every single deployment**. This was:
- ❌ **Anti-pattern**: Import is meant to be one-time
- ❌ **Slow**: Added 30-60 seconds to every deployment
- ❌ **Risky**: Could corrupt state if imports behaved unexpectedly
- ❌ **Unnecessary**: Resources stay in state after first import

### The Solution (Now)

We separated concerns:
- 📦 **Deployment workflow**: Fast, reliable, runs on every push
- 🔧 **Import workflow**: Manual, one-time, for setup/migration only

This follows infrastructure-as-code best practices:
- ✅ Import is an exceptional operation, not routine
- ✅ Faster deployments
- ✅ Clearer workflow purposes
- ✅ Reduced risk of state issues

---

## Terraform State Management

### Where is the state stored?

Terraform state is stored in **Azure Storage**:
- Storage Account: `stpcomcpprodeus` (from `TF_STATE_STORAGE_ACCOUNT` variable)
- Container: `tfstate` (from `TF_STATE_CONTAINER` variable)
- Blob: `terraform.tfstate`

### Why remote state?

Remote state allows:
- Multiple team members to collaborate
- GitHub Actions to access the same state
- State locking to prevent concurrent modifications
- Automatic backup and versioning

### Once imported, always imported

After you run the import workflow once:
- Resources are recorded in `terraform.tfstate` in Azure Storage
- Every subsequent workflow run reads this state
- You **never need to import again** (unless adding new resources)

---

## Troubleshooting

### "Resource already exists" error during deployment

**Cause**: Terraform is trying to create a resource that already exists in Azure but isn't in Terraform state.

**Solution**: Run the **"Terraform Import Existing Resources"** workflow once.

### "Resource not found in state" error

**Cause**: Terraform state is out of sync with Azure (resource was deleted manually).

**Solution**:
1. If resource should exist: Re-create it in Azure, then import
2. If resource should NOT exist: Remove from Terraform config or run `terraform state rm <resource>`

### Deployment workflow keeps failing

**Cause**: Check the specific error, but common issues:
- Container App in Failed state (workflow now handles this automatically)
- Secrets not configured in GitHub
- Identity permissions not set up correctly

**Solution**: Review the workflow logs for specific errors. The workflow is now resilient to most common failures.

---

## Best Practices

### ✅ DO

- Use the deployment workflow for all regular deployments
- Run import workflow only when explicitly needed
- Review Terraform plan output after imports
- Keep Terraform state in Azure Storage (never commit locally)
- Use semantic versioning for Docker images (not just "latest")

### ❌ DON'T

- Run import workflow repeatedly "just to be safe"
- Manually edit Terraform state files
- Delete Terraform state without backup
- Force-push Terraform state changes
- Skip reviewing Terraform plan before applying

---

## Summary

| Workflow | When | Frequency | Purpose |
|----------|------|-----------|---------|
| **Deploy to Azure Container Apps** | Every push to main | Continuous | Deploy application |
| **Terraform Import Existing Resources** | Manual only | One-time | Import existing infrastructure |

**Remember**: Import once, deploy many times! 🚀
