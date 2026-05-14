#requires -Version 5.1
<#
.SYNOPSIS
  One-shot bootstrap for adspy: install deps, start Postgres, migrate, launch API + worker + dashboard.

.NOTES
  Run from the repo root: powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
#>

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function OK($msg)   { Write-Host "  [ok] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  [!]  $msg" -ForegroundColor Yellow }

Step "1/7 verifying prerequisites"
foreach ($tool in @("python", "poetry", "docker", "node", "npm")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Host "  missing: $tool" -ForegroundColor Red
        Write-Host "  install it and re-run. python>=3.12, poetry, Docker Desktop, node>=20." -ForegroundColor Red
        exit 1
    }
}
OK "python, poetry, docker, node, npm all present"

Step "2/7 .env"
$envPath = Join-Path $root ".env"
if (-not (Test-Path $envPath)) {
    Copy-Item (Join-Path $root ".env.example") $envPath
    Warn ".env created from .env.example — fill in META_GRAPH_TOKEN / GEMINI_API_KEY / GROQ_API_KEY before scraping"
} else {
    OK ".env exists"
}

Step "3/7 poetry install + playwright chromium"
Push-Location $root
poetry install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
poetry run playwright install chromium
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Pop-Location
OK "python deps + chromium installed"

Step "4/7 docker compose up (postgres+pgvector)"
docker compose -f (Join-Path $root "docker-compose.yml") up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "  waiting for postgres to be healthy..."
$tries = 0
while ($tries -lt 30) {
    $status = docker compose -f (Join-Path $root "docker-compose.yml") ps --format json | ConvertFrom-Json
    $pg = $status | Where-Object { $_.Service -eq "postgres" }
    if ($pg -and $pg.Health -eq "healthy") { break }
    Start-Sleep -Seconds 2
    $tries++
}
OK "postgres up"

Step "5/7 alembic migrate"
Push-Location $root
poetry run alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Pop-Location
OK "schema migrated (0001 + 0002 + 0003)"

Step "6/7 dashboard npm install"
$dashPath = Join-Path $root "dashboard"
$envLocalPath = Join-Path $dashPath ".env.local"
if (-not (Test-Path $envLocalPath)) {
    Copy-Item (Join-Path $dashPath ".env.example") $envLocalPath
}
Push-Location $dashPath
if (-not (Test-Path (Join-Path $dashPath "node_modules"))) {
    npm install
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Pop-Location
OK "dashboard deps installed"

Step "7/7 ready"
Write-Host @"

Everything is set up. Three things to run (each in its own terminal):

  Terminal 1  (API):
    cd $root
    make api

  Terminal 2  (worker):
    cd $root
    make worker

  Terminal 3  (dashboard):
    cd $dashPath
    npm run dev

Then visit:
  http://localhost:3000   — dashboard
  http://localhost:8000/docs  — API docs

To trigger a scrape, either:
  - hit POST http://localhost:8000/scrape/meta with a JSON body, or
  - use the UI at http://localhost:3000/scrape

(Don't forget to fill META_GRAPH_TOKEN, GEMINI_API_KEY, GROQ_API_KEY in .env first.)
"@ -ForegroundColor Green
