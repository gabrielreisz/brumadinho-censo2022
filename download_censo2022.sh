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
DEST_MALHA="$(dirname "$DEST")/malha"
DEST_SETORES="$(dirname "$DEST")/setores"
DEST_2010="$(dirname "$DEST")/censo2010"

mkdir -p "$DEST" "$DEST_MALHA" "$DEST_SETORES" "$DEST_2010"
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
  "Agregados_por_Distrito_csv/Agregados_por_distritos_obitos_BR.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_pessoas_quilombolas_BR.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_domicilios_quilombolas_BR.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_pessoas_indigenas_BR.zip"
  "Agregados_por_Distrito_csv/Agregados_por_distritos_domicilios_indigenas_BR.zip"
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

# A malha dos distritos (shapefile) vai para outra pasta porque nao e um CSV
# de agregados - quem le e o 05_malha_distritos.py, nao o 01_processar_censo.py
MALHA="malha_com_atributos/distritos/shp/UF/MG/MG_distritos_CD2022.zip"
if [ -f "$DEST_MALHA/MG_distritos_CD2022.zip" ]; then
  echo "[skip] MG_distritos_CD2022.zip ja existe"
else
  echo "[baixando] MG_distritos_CD2022.zip (malha dos distritos de MG)"
  if ! curl -L --fail --retry 3 -o "$DEST_MALHA/MG_distritos_CD2022.zip" "$BASE/$MALHA"; then
    echo "  [FALHOU] MG_distritos_CD2022.zip"
    rm -f "$DEST_MALHA/MG_distritos_CD2022.zip"
    FALHAS+=("MG_distritos_CD2022.zip")
  fi
fi

# Agregados e malha por setor censitario: nivel abaixo do distrito, usados pelo
# 10_setores_censitarios.py no mapa de calor
SETORES=(
  "malha_com_atributos/setores/shp/UF/MG/MG_setores_CD2022.zip"
  "Agregados_por_Setor_csv/Agregados_por_setores_basico_BR_20260520.zip"
  "Agregados_por_Setor_csv/Agregados_por_setores_caracteristicas_domicilio2_BR_20250417.zip"
  "Agregados_por_Setor_csv/Agregados_por_setores_demografia_BR.zip"
)
for f in "${SETORES[@]}"; do
  fname="$(basename "$f")"
  if [ -f "$DEST_SETORES/$fname" ]; then
    echo "[skip] $fname ja existe"
    continue
  fi
  echo "[baixando] $fname"
  if ! curl -L --fail --retry 3 -o "$DEST_SETORES/$fname" "$BASE/$f"; then
    echo "  [FALHOU] $fname"
    rm -f "$DEST_SETORES/$fname"
    FALHAS+=("$fname")
  fi
done

# Censo 2010 por setor censitario: serie historica e renda por distrito
BASE_2010="https://ftp.ibge.gov.br/Censos/Censo_Demografico_2010/Resultados_do_Universo/Agregados_por_Setores_Censitarios"
if [ -f "$DEST_2010/MG_20260615.zip" ]; then
  echo "[skip] MG_20260615.zip ja existe"
else
  echo "[baixando] MG_20260615.zip (Censo 2010, setores de MG)"
  if ! curl -L --fail --retry 3 -o "$DEST_2010/MG_20260615.zip" "$BASE_2010/MG_20260615.zip"; then
    echo "  [FALHOU] MG_20260615.zip"
    rm -f "$DEST_2010/MG_20260615.zip"
    FALHAS+=("MG_20260615.zip")
  fi
fi

echo
if [ ${#FALHAS[@]} -eq 0 ]; then
  echo "Concluído sem falhas. Arquivos em: $DEST"
else
  echo "Concluído COM FALHAS nos seguintes arquivos (o IBGE pode ter renomeado o arquivo):"
  printf '  - %s\n' "${FALHAS[@]}"
  echo "Confira o nome atual em $BASE/Agregados_por_Distrito_csv/"
fi
echo
du -sh "$DEST" "$DEST_MALHA" "$DEST_SETORES" "$DEST_2010"
