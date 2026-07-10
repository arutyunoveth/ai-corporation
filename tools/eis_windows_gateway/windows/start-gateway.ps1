param(
  [string]$StunnelPath = "stunnel.exe",
  [string]$ConfigPath = "$env:USERPROFILE\Arvectum\EisServicesVbsTest\config\stunnel-int44.conf"
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }
$listener = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8110 -ErrorAction SilentlyContinue
if ($listener) { throw "Port 127.0.0.1:8110 is already in use" }
Start-Process -FilePath $StunnelPath -ArgumentList @($ConfigPath) -WindowStyle Hidden
