param(
  [int]$Port = 8110,
  [string]$HostHeader = "int44.zakupki.gov.ru"
)

$url = "http://127.0.0.1:$Port/eis-integration/services-vbs?wsdl"
curl.exe -v $url -H "Host: $HostHeader"
