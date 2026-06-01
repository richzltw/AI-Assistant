param(
  [string]$ProjectId = "project-40161111-553e-4592-93c",
  [string]$Region = "us-central1",
  [string]$Service = "gcp-multimodal-assistant"
)

$ErrorActionPreference = "Stop"

# Snapshot values captured before the latest deploy.
$KnownGoodRevision = "gcp-multimodal-assistant-00022-qrf"
$ServiceBackupFile = "backups/cloudrun/gcp-multimodal-assistant-service-20260601-001250.yaml"

Write-Host "Setting project to $ProjectId"
gcloud config set project $ProjectId

Write-Host "Rolling traffic back to known-good revision: $KnownGoodRevision"
gcloud run services update-traffic $Service `
  --region=$Region `
  --to-revisions="$KnownGoodRevision=100"

Write-Host "Rollback traffic update complete."
Write-Host "Optional full spec restore command:"
Write-Host "gcloud run services replace $ServiceBackupFile --region=$Region --project=$ProjectId"
