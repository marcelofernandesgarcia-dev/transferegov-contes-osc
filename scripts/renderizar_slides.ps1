# Renderiza cada slide de um .pptx em PNG e grava o texto de cada slide em JSON, pelo PowerPoint instalado.
# O .pptx é aberto somente para leitura e não é copiado para o site.
# Uso: powershell -File scripts\renderizar_slides.ps1 -Arquivo "<.pptx>" -Saida "<pasta>" [-Largura 1600]
param(
  [Parameter(Mandatory = $true)][string]$Arquivo,
  [Parameter(Mandatory = $true)][string]$Saida,
  [int]$Largura = 1600
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Arquivo)) { throw "Apresentação não encontrada: $Arquivo" }
New-Item -ItemType Directory -Force -Path $Saida | Out-Null
$app = New-Object -ComObject PowerPoint.Application
try {
  $p = $app.Presentations.Open($Arquivo, $true, $false, $false)  # somente leitura, sem janela
  $altura = [int][math]::Round($Largura * $p.PageSetup.SlideHeight / $p.PageSetup.SlideWidth)
  $slides = @()
  foreach ($s in $p.Slides) {
    $n = '{0:D2}' -f $s.SlideIndex
    $png = Join-Path $Saida "slide-$n.png"
    $s.Export($png, 'PNG', $Largura, $altura)
    $textos = @()
    foreach ($sh in $s.Shapes) {
      if ($sh.HasTextFrame -and $sh.TextFrame.HasText) {
        $t = $sh.TextFrame.TextRange.Text -replace "`r", "`n"
        if ($t.Trim()) { $textos += $t.Trim() }
      }
      if ($sh.HasTable) {
        foreach ($l in 1..$sh.Table.Rows.Count) {
          $celulas = @()
          foreach ($c in 1..$sh.Table.Columns.Count) { $celulas += $sh.Table.Cell($l, $c).Shape.TextFrame.TextRange.Text.Trim() }
          $textos += ($celulas -join ' | ')
        }
      }
    }
    # Hyperlinks do slide (texto exibido e endereço), na ordem em que aparecem
    $links = @()
    foreach ($h in $s.Hyperlinks) {
      if ($h.Address) { $links += [pscustomobject]@{ texto = ([string]$h.TextToDisplay).Trim(); endereco = [string]$h.Address } }
    }
    # Texto alternativo das imagens do slide (o montador decide quais citar)
    $imagens = @()
    foreach ($sh in $s.Shapes) {
      if ($sh.Type -eq 13 -and $sh.AlternativeText) { $imagens += ([string]$sh.AlternativeText).Trim() }
    }
    $slides += [pscustomobject]@{ numero = $s.SlideIndex; imagem = "slide-$n.png"; largura = $Largura; altura = $altura; textos = $textos; links = $links; imagens = $imagens }
  }
  $p.Close()
  $json = ConvertTo-Json -InputObject $slides -Depth 5
  [System.IO.File]::WriteAllText((Join-Path $Saida 'slides.json'), $json, (New-Object System.Text.UTF8Encoding($false)))
  Write-Output "$($slides.Count) slides em $Saida"
} finally {
  $app.Quit()
}
