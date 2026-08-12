# valida_sgs.ps1 -- consulta o CATALOGO oficial do SGS/BCB para confirmar o nome,
# a periodicidade e a unidade de cada codigo de serie ANTES de usa-lo no painel.
# Endpoint oficial (fachada SOAP do SGS):
#   https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?method=getUltimoValorXML&codigoSerie={codigo}
# Grava o XML bruto de resposta em data_raw/sgs/catalogo/ para a nota de verificacao.
param(
  [int[]]$Codigos,
  [string]$OutDir = "$PSScriptRoot\..\data_raw\sgs\catalogo"
)
$ProgressPreference = 'SilentlyContinue'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$res = foreach ($c in $Codigos) {
  $url = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?method=getUltimoValorXML&codigoSerie=$c"
  try {
    $r = Invoke-WebRequest -Uri $url -TimeoutSec 40 -UseBasicParsing
    $raw = $r.Content
    Set-Content -Path (Join-Path $OutDir "sgs_$c.xml") -Value $raw -Encoding utf8
    # o payload vem HTML-escapado dentro do envelope SOAP
    $inner = [System.Net.WebUtility]::HtmlDecode($raw)
    function Get-Tag($t) { if ($inner -match "<$t>(.*?)</$t>") { $Matches[1].Trim() } else { "" } }
    [pscustomobject]@{
      Codigo        = $c
      Nome          = Get-Tag 'NOME'
      Periodicidade = Get-Tag 'PERIODICIDADE'
      Unidade       = Get-Tag 'UNIDADE'
      UltimaData    = (Get-Tag 'DATA') + '/' + (Get-Tag 'ANO')
      UltimoValor   = Get-Tag 'VALOR'
      Status        = if ($inner -match "status='2'") { 'CONFIRMADO' } else { 'NAO CONFIRMADO' }
    }
  } catch {
    [pscustomobject]@{ Codigo=$c; Nome=''; Periodicidade=''; Unidade=''; UltimaData=''; UltimoValor=''; Status="ERRO: $($_.Exception.Message)" }
  }
}
$res | Format-Table -AutoSize -Wrap
$res | Export-Csv -Path (Join-Path $OutDir "catalogo_sgs_validado.csv") -NoTypeInformation -Encoding utf8
