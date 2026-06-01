param(
  [Parameter(Mandatory = $true)][string]$ProjectId,
  [string]$Region = "us-central1",
  [string]$Service = "gcp-multimodal-assistant"
)

$ErrorActionPreference = "Stop"

Write-Host "Setting project to $ProjectId"
gcloud config set project $ProjectId

Write-Host "Enabling required services"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com speech.googleapis.com texttospeech.googleapis.com firestore.googleapis.com

$Repo = "assistant"
$Image = "${Region}-docker.pkg.dev/$ProjectId/$Repo/${Service}:latest"

Write-Host "Ensuring Artifact Registry repo exists"
$PrevErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$RepoExists = gcloud artifacts repositories list --quiet --location=$Region --filter="name~/$Repo$" --format="value(name)" 2>$null
$ErrorActionPreference = $PrevErrorActionPreference
if (-not $RepoExists) {
  Write-Host "Artifact Registry repo '$Repo' not found. Creating..."
  gcloud artifacts repositories create $Repo --quiet --repository-format=docker --location=$Region
} else {
  Write-Host "Artifact Registry repo '$Repo' already exists."
}

Write-Host "Building and pushing container image with Cloud Build"
gcloud builds submit --tag $Image .
if ($LASTEXITCODE -ne 0) { throw "Cloud Build failed." }

Write-Host "Deploying image to Cloud Run using current authenticated account"
$EnvVars = "PROJECT_ID=$ProjectId,REGION=$Region,SERVICE_NAME=$Service,GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_GENAI_USE_VERTEXAI=true"
gcloud run deploy $Service --image=$Image --region=$Region --platform=managed --allow-unauthenticated "--set-env-vars=$EnvVars"
if ($LASTEXITCODE -ne 0) { throw "Cloud Run deploy failed." }

Write-Host "Deployment complete"
$Url = gcloud run services describe $Service --region $Region --format "value(status.url)"
Write-Host "Service URL: $Url"
