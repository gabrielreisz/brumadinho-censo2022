"""
Recorta o Censo Escolar (INEP) para os distritos de Brumadinho.

Diferente do CNES, aqui nao e preciso cruzamento geografico: os microdados do
INEP ja trazem CO_DISTRITO com o codigo do IBGE.

Le dois arquivos de dentro do ZIP de microdados:
    Tabela_Escola_*.csv     - uma linha por escola, com infraestrutura e equipe
    Tabela_Matricula_*.csv  - uma linha por escola, com matriculas por etapa

Gera:
    data/processed/inep_escolas_brumadinho.csv
"""

from __future__ import annotations

import csv
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CD_MUNICIPIO_BRUMADINHO, DIR_PROCESSED, DIR_RAW_INEP

ANO = 2025
URL = f"https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_{ANO}_.zip"
NOME_ZIP = f"microdados_censo_escolar_{ANO}.zip"

COLUNAS_ESCOLA = [
    "CO_ENTIDADE", "NO_ENTIDADE", "CO_DISTRITO", "NO_DISTRITO",
    "TP_DEPENDENCIA", "TP_LOCALIZACAO", "TP_LOCALIZACAO_DIFERENCIADA",
    "TP_SITUACAO_FUNCIONAMENTO", "QT_SALAS_UTILIZADAS",
    "IN_AGUA_POTAVEL", "IN_AGUA_REDE_PUBLICA", "IN_ENERGIA_REDE_PUBLICA",
    "IN_ESGOTO_REDE_PUBLICA", "IN_LIXO_SERVICO_COLETA", "IN_INTERNET",
    "IN_BIBLIOTECA", "IN_LABORATORIO_INFORMATICA", "IN_QUADRA_ESPORTES",
    "IN_ACESSIBILIDADE_INEXISTENTE", "IN_ALIMENTACAO",
    "IN_MATERIAL_PED_QUILOMBOLA", "IN_MATERIAL_PED_INDIGENA",
]
COLUNAS_MATRICULA = [
    "CO_ENTIDADE", "QT_MAT_BAS", "QT_MAT_INF", "QT_MAT_INF_CRE", "QT_MAT_INF_PRE",
    "QT_MAT_FUND", "QT_MAT_FUND_AI", "QT_MAT_FUND_AF", "QT_MAT_MED",
]

# Codigos do dicionario do INEP
DEPENDENCIA = {1: "Federal", 2: "Estadual", 3: "Municipal", 4: "Privada"}
LOCALIZACAO = {1: "Urbana", 2: "Rural"}
LOCALIZACAO_DIFERENCIADA = {
    0: "Não está em área diferenciada",
    1: "Área de assentamento",
    2: "Terra indígena",
    3: "Área remanescente de quilombo",
    6: "Área remanescente de quilombo",
    7: "Área de assentamento",
    8: "Terra indígena",
}
SITUACAO = {1: "Em atividade", 2: "Paralisada", 3: "Extinta", 4: "Extinta no ano anterior"}


def baixar() -> Path:
    DIR_RAW_INEP.mkdir(parents=True, exist_ok=True)
    destino = DIR_RAW_INEP / NOME_ZIP
    if destino.exists():
        print(f"[skip] {destino.name} ja existe")
        return destino
    print(f"baixando {URL} (~530 MB) ...")
    urllib.request.urlretrieve(URL, destino)
    return destino


def _ler_do_zip(zf: zipfile.ZipFile, prefixo: str, colunas: list[str]) -> pd.DataFrame:
    """Le so as linhas de Brumadinho, sem descompactar o arquivo inteiro em disco."""
    nome = next(n for n in zf.namelist() if Path(n).name.startswith(prefixo) and n.endswith(".csv"))
    with zf.open(nome) as bruto:
        fluxo = csv.reader(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")
        cabecalho = next(fluxo)
        idx_mun = cabecalho.index("CO_MUNICIPIO")
        indices = {c: cabecalho.index(c) for c in colunas if c in cabecalho}
        linhas = [
            {c: linha[i] for c, i in indices.items()}
            for linha in fluxo
            if linha[idx_mun] == CD_MUNICIPIO_BRUMADINHO
        ]
    print(f"  {nome.split('/')[-1]}: {len(linhas)} escolas de Brumadinho")
    return pd.DataFrame(linhas)


def gerar() -> pd.DataFrame:
    caminho = baixar()
    with zipfile.ZipFile(caminho) as zf:
        escolas = _ler_do_zip(zf, "Tabela_Escola", COLUNAS_ESCOLA)
        matriculas = _ler_do_zip(zf, "Tabela_Matricula", COLUNAS_MATRICULA)

    df = escolas.merge(matriculas, on="CO_ENTIDADE", how="left")
    for coluna in df.columns:
        if coluna.startswith(("QT_", "TP_", "IN_")) or coluna.startswith("CO_"):
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    df["dependencia"] = df["TP_DEPENDENCIA"].map(DEPENDENCIA)
    df["localizacao"] = df["TP_LOCALIZACAO"].map(LOCALIZACAO)
    df["area_diferenciada"] = df["TP_LOCALIZACAO_DIFERENCIADA"].fillna(0).map(LOCALIZACAO_DIFERENCIADA)
    df["situacao"] = df["TP_SITUACAO_FUNCIONAMENTO"].map(SITUACAO)
    df["distrito"] = df["NO_DISTRITO"]

    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    destino = DIR_PROCESSED / "inep_escolas_brumadinho.csv"
    df.to_csv(destino, index=False, encoding="utf-8")
    print(df.groupby("distrito")["QT_MAT_BAS"].agg(escolas="size", matriculas="sum").to_string())
    print(f"-> {destino}")
    return df


if __name__ == "__main__":
    gerar()
