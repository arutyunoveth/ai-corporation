$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

$paths = @(
  "C:\Program Files\Crypto Pro",
  "C:\Program Files (x86)\Crypto Pro",
  "C:\Program Files\Aktiv Co",
  "C:\Program Files\Rutoken",
  "C:\Program Files (x86)\Rutoken"
)

[PSCustomObject]@{
  Windows = (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture)
  Is64BitOS = [Environment]::Is64BitOperatingSystem
  Is64BitProcess = [Environment]::Is64BitProcess
  Commands = @("csptest.exe", "certmgr.exe", "cryptcp.exe", "stunnel.exe", "curl.exe") | ForEach-Object {
    $cmd = Get-Command $_ -ErrorAction SilentlyContinue
    [PSCustomObject]@{ Name = $_; Found = [bool]$cmd; Source = if ($cmd) { $cmd.Source } else { $null } }
  }
  Directories = $paths | ForEach-Object { [PSCustomObject]@{ Path = $_; Exists = Test-Path $_ } }
} | ConvertTo-Json -Depth 5
