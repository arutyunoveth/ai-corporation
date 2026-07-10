$ports = @(8110, 8111)
[PSCustomObject]@{
  Processes = Get-Process stunnel -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, Path
  Listeners = foreach ($port in $ports) { Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $port -ErrorAction SilentlyContinue }
} | ConvertTo-Json -Depth 4
