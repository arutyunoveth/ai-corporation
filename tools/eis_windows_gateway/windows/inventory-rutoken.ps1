$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

function Mask-LongValue($value) {
  if (-not $value) { return $null }
  $text = [string]$value
  if ($text.Length -le 10) { return "***" }
  return $text.Substring(0, 6) + "..." + $text.Substring($text.Length - 4)
}

$csptest = "C:\Program Files\Crypto Pro\CSP\csptest.exe"
$containers = if (Test-Path $csptest) { & $csptest -keyset -enum_cont -fqcn 2>&1 | Out-String } else { "csptest.exe not found" }

$certs = foreach ($store in @("Cert:\CurrentUser\My", "Cert:\LocalMachine\My")) {
  if (Test-Path $store) {
    Get-ChildItem $store -ErrorAction SilentlyContinue | ForEach-Object {
      [PSCustomObject]@{
        Store = $store
        SubjectMasked = ($_.Subject -replace "([A-Fa-f0-9]{8,})", "***")
        IssuerMasked = ($_.Issuer -replace "([A-Fa-f0-9]{8,})", "***")
        NotBefore = $_.NotBefore
        NotAfter = $_.NotAfter
        HasPrivateKey = $_.HasPrivateKey
        EKU = @($_.EnhancedKeyUsageList | ForEach-Object { $_.FriendlyName })
        ThumbprintMasked = Mask-LongValue $_.Thumbprint
        SerialMasked = Mask-LongValue $_.SerialNumber
      }
    }
  }
}

[PSCustomObject]@{
  ContainersRawMasked = ($containers -replace "\\\\\.\\[^`r`n]+", "\\\\.\\***masked-container***")
  Certificates = $certs
} | ConvertTo-Json -Depth 6
