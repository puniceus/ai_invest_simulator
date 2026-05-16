param(
    [string]$HostName = "150.230.249.92",
    [string]$User = "ubuntu",
    [string]$RemotePath = "/home/ubuntu/ai-invest-simulator",
    [string]$WebHtml = "/var/www/html/simulator.html"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

ssh "$User@$HostName" "mkdir -p $RemotePath"
rsync -av --delete `
    --exclude ".git" `
    --exclude "venv" `
    --exclude ".venv" `
    --exclude "__pycache__" `
    --exclude ".pytest_cache" `
    --exclude "data/state.json" `
    --exclude "reports/*.html" `
    "$ProjectRoot/" "$User@$HostName`:$RemotePath/"

ssh "$User@$HostName" "cd $RemotePath && python3 -m venv venv && ./venv/bin/python -m pip install --upgrade pip && ./venv/bin/pip install -r requirements.txt"
ssh "$User@$HostName" "cd $RemotePath && ./venv/bin/python -m app.cli run && sudo cp reports/simulator.html $WebHtml"

