# varre_catalogo_sgs.ps1 -- varre faixas de codigos do SGS e registra o NOME OFICIAL
# de cada serie existente. Serve para DESCOBRIR o codigo correto pelo nome publicado
# pelo BCB, em vez de chutar um codigo "plausivel".
# Saida: data_raw/sgs/catalogo/varredura_sgs.csv
param(
  [string]$OutDir = "$PSScriptRoot\..\data_raw\sgs\catalogo"
)
$ProgressPreference = 'SilentlyContinue'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# blocos publicados pelo BCB nas "Estatisticas monetarias e de credito"
$faixas = New-Object System.Collections.Generic.List[int]
foreach ($r in @(
  ,(20539,20800)   # saldos da carteira por recurso/modalidade
  ,(20801,20900)   # concessoes
  ,(21082,21150)   # inadimplencia por modalidade
  ,(21255,21310)   # atrasos / carteira por nivel de risco
  ,(25400,25420)   # endividamento e comprometimento de renda das familias
)) { ($r[0]..$r[1]) | ForEach-Object { $faixas.Add($_) } }

$out = New-Object System.Collections.Generic.List[object]
foreach ($c in $faixas) {
  $url = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?method=getUltimoValorXML&codigoSerie=$c"
  try {
    $raw = (Invoke-WebRequest -Uri $url -TimeoutSec 25 -UseBasicParsing).Content
    $inner = [System.Net.WebUtility]::HtmlDecode($raw)
    if ($inner -match '<NOME>(.*?)</NOME>') {
      $nome = $Matches[1].Trim()
      $per = if ($inner -match '<PERIODICIDADE>(.*?)</PERIODICIDADE>') { $Matches[1].Trim() } else { '' }
      $uni = if ($inner -match '<UNIDADE>(.*?)</UNIDADE>') { $Matches[1].Trim() } else { '' }
      if ($nome) { $out.Add([pscustomobject]@{ Codigo=$c; Nome=$nome; Periodicidade=$per; Unidade=$uni }) }
    }
  } catch { }
}
$out | Export-Csv -Path (Join-Path $OutDir 'varredura_sgs.csv') -NoTypeInformation -Encoding utf8
"Series encontradas: $($out.Count)"
