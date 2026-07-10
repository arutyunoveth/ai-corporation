$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

$roots = @("C:\Program Files\Crypto Pro", "C:\Program Files (x86)\Crypto Pro")
$files = foreach ($root in $roots) {
  if (Test-Path $root) {
    Get-ChildItem $root -Recurse -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match "stunnel|csptest|certmgr|cryptcp" } |
      Select-Object FullName, Length, LastWriteTime
  }
}

$binaries = foreach ($file in $files) {
  $sig = Get-AuthenticodeSignature $file.FullName
  $item = Get-Item $file.FullName
  [PSCustomObject]@{
    Path = $file.FullName
    Length = $file.Length
    ProductVersion = $item.VersionInfo.ProductVersion
    FileVersion = $item.VersionInfo.FileVersion
    SignatureStatus = $sig.Status.ToString()
    Signer = if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { $null }
  }
}

[PSCustomObject]@{
  Files = $files
  Binaries = $binaries
} | ConvertTo-Json -Depth 6
