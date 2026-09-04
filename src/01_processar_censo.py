# -*- coding: utf-8 -*-
"""
01_processar_censo.py
======================
Lê os ZIPs do Censo 2022 (produto "Agregados por Distrito" do IBGE) em
data/raw/censo2022/, filtra as linhas de São José do Paraopeba e Conceição
de Itaguá (distritos de Brumadinho-MG) e grava CSV + Parquet em
data/processed/.

Uso:
    python src/01_processar_censo.py --inspect   # só mostra as colunas
    python src/01_processar_censo.py              # processa tudo
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED, DIR_RAW_CENSO, DISTRITOS_ALVO

CANDIDATOS_COL_CD_DIST = ["CD_DIST", "CD_DISTRITO", "COD_DISTRITO", "CD_DIST_CENSO"]
CANDIDATOS_COL_CD_MUN = ["CD_MUN", "CD_MUNICIPIO", "COD_MUNICIPIO"]

# Encoding/separador dos arquivos do IBGE variam por produto — tenta essas combinações
ENCODING_TENTATIVAS = ["latin1", "utf-8", "cp1252"]
SEP_TENTATIVAS = [";", ","]


def _ler_csv_de_dentro_do_zip(caminho_zip: Path) -> dict[str, pd.DataFrame]:
    """Abre um .zip do IBGE e lê todo CSV dentro dele, testando combinações
    de encoding/separador até uma funcionar."""
    resultado: dict[str, pd.DataFrame] = {}
    with zipfile.ZipFile(caminho_zip) as zf:
        nomes_csv = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not nomes_csv:
            print(f"  [aviso] nenhum .csv encontrado dentro de {caminho_zip.name}")
            return resultado

        for nome_csv in nomes_csv:
            df = None
            ultimo_erro = None
            for enc in ENCODING_TENTATIVAS:
                for sep in SEP_TENTATIVAS:
                    try:
                        with zf.open(nome_csv) as f:
                            df = pd.read_csv(f, sep=sep, encoding=enc, low_memory=False)
                        if df.shape[1] <= 1:
                            df = None
                            continue
                        break
                    except (UnicodeDecodeError, pd.errors.ParserError) as e:
                        ultimo_erro = e
                        continue
                if df is not None:
                    break

            if df is None:
                print(f"  [erro] não consegui ler {nome_csv}. Último erro: {ultimo_erro}")
                continue

            resultado[nome_csv] = df
    return resultado


def _achar_coluna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    """Procura a primeira coluna que bate com algum nome candidato (case-insensitive)."""
    colunas_normalizadas = {c.strip().upper(): c for c in df.columns}
    for candidato in candidatos:
        if candidato.upper() in colunas_normalizadas:
            return colunas_normalizadas[candidato.upper()]
    return None


def filtrar_distritos_alvo(df: pd.DataFrame, nome_origem: str) -> pd.DataFrame | None:
    """Mantém só as linhas de Conceição de Itaguá e São José do Paraopeba,
    adicionando a coluna 'distrito_alvo' com o nome amigável."""
    col_cd_dist = _achar_coluna(df, CANDIDATOS_COL_CD_DIST)

    if col_cd_dist is not None:
        codigos = df[col_cd_dist].astype(str).str.strip().str.zfill(9)
        filtrado = df[codigos.isin(DISTRITOS_ALVO.keys())].copy()
        filtrado["distrito_alvo"] = codigos[codigos.isin(DISTRITOS_ALVO.keys())].map(DISTRITOS_ALVO)
        if filtrado.empty:
            print(
                f"  [aviso] coluna '{col_cd_dist}' encontrada em {nome_origem}, mas "
                f"nenhuma linha bateu com os códigos {list(DISTRITOS_ALVO)}."
            )
        return filtrado

    col_cd_mun = _achar_coluna(df, CANDIDATOS_COL_CD_MUN)
    if col_cd_mun is not None:
        print(f"  [info] {nome_origem} não tem coluna de distrito com 9 dígitos; sem fallback implementado para esse formato.")
        return None

    print(f"  [aviso] não encontrei coluna de distrito em {nome_origem}. Colunas disponíveis: {list(df.columns)}")
    return None


def inspecionar(zips: list[Path]) -> None:
    """Modo --inspect: mostra as colunas de cada CSV sem processar nada."""
    for caminho_zip in zips:
        print(f"\n=== {caminho_zip.name} ===")
        tabelas = _ler_csv_de_dentro_do_zip(caminho_zip)
        for nome_csv, df in tabelas.items():
            print(f"  arquivo interno: {nome_csv}")
            print(f"  linhas: {len(df):,} | colunas: {len(df.columns)}")
            print(f"  colunas: {list(df.columns)}")
            print(f"  amostra:\n{df.head(3).to_string(max_cols=8)}\n")


def processar(zips: list[Path]) -> None:
    """Filtra cada arquivo para os 2 distritos-alvo e salva em data/processed/."""
    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)

    for caminho_zip in zips:
        tema = caminho_zip.stem.replace("Agregados_por_distritos_", "").split("_BR")[0]
        print(f"\nProcessando tema: {tema} ({caminho_zip.name})")

        tabelas = _ler_csv_de_dentro_do_zip(caminho_zip)
        for nome_csv, df in tabelas.items():
            filtrado = filtrar_distritos_alvo(df, nome_csv)
            if filtrado is None or filtrado.empty:
                continue

            destino_csv = DIR_PROCESSED / f"censo2022_{tema}_distritos.csv"
            destino_parquet = DIR_PROCESSED / f"censo2022_{tema}_distritos.parquet"
            filtrado.to_csv(destino_csv, index=False, encoding="utf-8")
            print(f"  -> {len(filtrado)} linhas salvas em {destino_csv.relative_to(DIR_PROCESSED.parent.parent)}")
            try:
                filtrado.to_parquet(destino_parquet, index=False)
            except ImportError:
                print("  [aviso] Parquet não gerado (instale 'pyarrow' se quiser esse formato também).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true", help="Só mostra as colunas de cada arquivo, sem processar nada.")
    args = parser.parse_args()

    if not DIR_RAW_CENSO.exists():
        print(f"Pasta não encontrada: {DIR_RAW_CENSO}")
        print("Baixe os arquivos do checklist (docs/01_mapeamento_extracao.md) antes de rodar este script — veja download_censo2022.sh.")
        sys.exit(1)

    zips = sorted(DIR_RAW_CENSO.glob("*.zip"))
    if not zips:
        print(f"Nenhum .zip encontrado em {DIR_RAW_CENSO}.")
        print("Baixe os arquivos do checklist antes de rodar este script.")
        sys.exit(1)

    print(f"Encontrados {len(zips)} arquivo(s) .zip em {DIR_RAW_CENSO}")

    if args.inspect:
        inspecionar(zips)
    else:
        processar(zips)


if __name__ == "__main__":
    main()
