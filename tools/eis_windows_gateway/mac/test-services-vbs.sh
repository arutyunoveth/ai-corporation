#!/usr/bin/env bash
set -euo pipefail

local_port="${1:-18110}"
host_header="${2:-int44.zakupki.gov.ru}"
curl -v "http://127.0.0.1:${local_port}/eis-integration/services-vbs?wsdl" -H "Host: ${host_header}"
