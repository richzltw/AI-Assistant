param(
  [Parameter(Mandatory = $true)][string]$ProjectId,
  [string]$Region = "us-central1",
  [string]$FunctionName = "daily-news-digest",
  [string]$SchedulerJobName = "daily-news-digest-7am",
  [string]$Schedule = "0 7 * * *",
  [string]$TimeZone = "America/Chicago",
  [string]$NewsFeeds = "https://news.google.com/rss,https://feeds.bbci.co.uk/news/world/rss.xml,https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
  [string]$DigestGeminiModel = "gemini-2.5-flash",
  [string]$SchedulerServiceAccountName = "scheduler-digest-invoker",
  [string]$SlackWebhookUrl = "",
  [string]$SlackBotToken = "",
  [string]$SlackDmEmail = "",
  [string]$TwilioAccountSid = "",
  [string]$TwilioAuthToken = "",
  [string]$TwilioFromNumber = "",
  [string]$TwilioToNumber = "",
  [string]$DigestFunctionToken = ""
)

$ErrorActionPreference = "Stop"

Write-Host "Setting gcloud project to $ProjectId"
gcloud config set project $ProjectId

Write-Host "Enabling required GCP services"
gcloud services enable cloudfunctions.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com cloudscheduler.googleapis.com run.googleapis.com

$FunctionSource = "scripts/news_digest_function"
$SchedulerServiceAccountEmail = "$SchedulerServiceAccountName@$ProjectId.iam.gserviceaccount.com"

Write-Host "Ensuring scheduler invoker service account exists"
$SaExists = gcloud iam service-accounts describe $SchedulerServiceAccountEmail --project $ProjectId --format="value(email)" 2>$null
if (-not $SaExists) {
  gcloud iam service-accounts create $SchedulerServiceAccountName --display-name "Scheduler Digest Invoker" --project $ProjectId
}

$EnvVars = @(
  "PROJECT_ID=$ProjectId",
  "REGION=$Region",
  "NEWS_FEEDS=$NewsFeeds",
  "DIGEST_GEMINI_MODEL=$DigestGeminiModel",
  "SLACK_WEBHOOK_URL=$SlackWebhookUrl",
  "SLACK_BOT_TOKEN=$SlackBotToken",
  "SLACK_DM_EMAIL=$SlackDmEmail",
  "TWILIO_ACCOUNT_SID=$TwilioAccountSid",
  "TWILIO_AUTH_TOKEN=$TwilioAuthToken",
  "TWILIO_FROM_NUMBER=$TwilioFromNumber",
  "TWILIO_TO_NUMBER=$TwilioToNumber",
  "DIGEST_FUNCTION_TOKEN=$DigestFunctionToken"
) -join ","

Write-Host "Deploying Cloud Function (2nd gen): $FunctionName"
gcloud functions deploy $FunctionName `
  --gen2 `
  --runtime=python312 `
  --region=$Region `
  --source=$FunctionSource `
  --entry-point=handler `
  --trigger-http `
  --no-allow-unauthenticated `
  --set-env-vars=$EnvVars

Write-Host "Granting Scheduler service account invoker permission"
gcloud functions add-invoker-policy-binding $FunctionName --region=$Region --member="serviceAccount:$SchedulerServiceAccountEmail"

$FunctionUrl = gcloud functions describe $FunctionName --region=$Region --format="value(serviceConfig.uri)"
if (-not $FunctionUrl) {
  throw "Failed to resolve function URL for $FunctionName"
}

Write-Host "Creating or updating Cloud Scheduler job: $SchedulerJobName"
$JobExists = gcloud scheduler jobs describe $SchedulerJobName --location=$Region --format="value(name)" 2>$null

if (-not $JobExists) {
  gcloud scheduler jobs create http $SchedulerJobName `
    --location=$Region `
    --schedule="$Schedule" `
    --time-zone="$TimeZone" `
    --uri="$FunctionUrl" `
    --http-method=POST `
    --headers="Content-Type=application/json" `
    --message-body='{"trigger":"cloud-scheduler"}' `
    --oidc-service-account-email="$SchedulerServiceAccountEmail" `
    --oidc-token-audience="$FunctionUrl"
} else {
  gcloud scheduler jobs update http $SchedulerJobName `
    --location=$Region `
    --schedule="$Schedule" `
    --time-zone="$TimeZone" `
    --uri="$FunctionUrl" `
    --http-method=POST `
    --headers="Content-Type=application/json" `
    --message-body='{"trigger":"cloud-scheduler"}' `
    --oidc-service-account-email="$SchedulerServiceAccountEmail" `
    --oidc-token-audience="$FunctionUrl"
}

Write-Host "News digest automation is configured."
Write-Host "Function URL: $FunctionUrl"
Write-Host "Schedule: $Schedule ($TimeZone)"
Write-Host "Run now (optional): gcloud scheduler jobs run $SchedulerJobName --location=$Region"
