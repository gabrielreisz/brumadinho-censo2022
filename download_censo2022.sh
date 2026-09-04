#!/usr/bin/env bash
# Baixa os arquivos do Censo 2022 (IBGE) - "Agregados por Distrito" - para
# data/raw/censo2022/. Rode direto no terminal (não dentro de ambientes com
# proxy/allowlist restrito, que podem bloquear ftp.ibge.gov.br).
#
# Uso: bash download_censo2022.sh [pasta_destino]

# Sem "set -e": um arquivo com nome desatualizado no servidor não pode
# derrubar o download dos demais.
set -uo pipefail

BASE="https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios"
DEST="${1:-$HOME/Documents/Work/Brumadinho/data/raw/censo2022}"

mkdir -p "$DEST"
echo "Salvando arquivos em: $DEST"
echo

# Nomes conferidos no índice do FTP em 04/09/2026
FILES=(
  "Agregados_por_Distrito_csv/Agregados_por_distritos_basico_BR_20260520.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_demografia_BR.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_cor_ou_raca_BR.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_alfabetizacao_BR.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_caracteristicas_domicilio1_BR.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_caracteristicas_domicilio2_BR_20250417.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_caracteristicas_domicilio3_BR_20250417.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_parentesco_BR.zip"
  "dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx"
)

FALHAS=()

for f in "${FILES[@]}"; do
  fname="$(basename "$f")"
  if [ -f "$DEST/$fname" ]; then
    echo "[skip] $fname já existe"
    continue
  fi
  echo "[baixando] $fname"
  if ! curl -L --fail --retry 3 -o "$DEST/$fname" "$BASE/$f"; then
    echo "  [FALHOU] $fname"
    rm -f "$DEST/$fname"
    FALHAS+=("$fname")
  fi
done

echo
if [ ${#FALHAS[@]} -eq 0 ]; then
  echo "Concluído sem falhas. Arquivos em: $DEST"
else
  echo "Concluído COM FALHAS nos seguintes arquivos (o IBGE pode ter renomeado o arquivo):"
  printf '  - %s\n' "${FALHAS[@]}"
  echo "Confira o nome atual em $BASE/Agregados_por_Distrito_csv/"
fi
echo
ls -lh "$DEST"
