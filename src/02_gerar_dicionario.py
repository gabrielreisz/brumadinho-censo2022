# -*- coding: utf-8 -*-
"""
02_gerar_dicionario.py
=======================
Lê o dicionário de dados oficial do IBGE (.xlsx baixado junto com os
Agregados por Distrito) e consolida as abas relevantes num único CSV, com a
coluna `variavel_num` normalizada — o IBGE usa `V0001` (4 dígitos) no tema
Básico mas `V00001`/`V01006` (5 dígitos) nos demais temas.

Uso:
    python src/02_gerar_dicionario.py
Gera:
    data/processed/dicionario_variaveis.csv
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED, DIR_RAW_CENSO

NOME_ARQUIVO_DICIONARIO = "dicionario_de_dados_agregados_por_setores_censitarios_20260520.xlsx"

ABAS_COM_VARIAVEL = [
    "Dicionário Básico",
    "Dicionário não PCT",
    "Dicionário PCT - Indígenas",
    "Dicionário PCT - Quilombolas",
]


def _numero_da_variavel(codigo: str) -> int | None:
    """'V0001' -> 1, 'V01006' -> 1006 — remove zeros à esquerda para casar
    códigos com paddings diferentes entre abas."""
    if not isinstance(codigo, str):
        return None
    m = re.match(r"^[Vv](\d+)$", codigo.strip())
    return int(m.group(1)) if m else None


def gerar() -> pd.DataFrame:
    caminho = DIR_RAW_CENSO / NOME_ARQUIVO_DICIONARIO
    if not caminho.exists():
        raise FileNotFoundError(
            f"Dicionário não encontrado em {caminho}. Baixe-o com "
            f"download_censo2022.sh antes de rodar este script."
        )

    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    linhas = []

    for aba in ABAS_COM_VARIAVEL:
        ws = wb[aba]
        cabecalho = None
        for row in ws.iter_rows(values_only=True):
            if cabecalho is None:
                cabecalho = [c.strip() if isinstance(c, str) else c for c in row]
                continue
            registro = dict(zip(cabecalho, row))
            codigo = registro.get("Variável")
            num = _numero_da_variavel(codigo)
            if num is None:
                continue
            linhas.append(
                {
                    "aba_origem": aba,
                    "variavel": codigo,
                    "variavel_num": num,
                    "tipo": registro.get("Tipo", ""),
                    "tema": registro.get("Tema", ""),
                    "descricao": registro.get("Descrição", ""),
                }
            )

    df = pd.DataFrame(linhas)
    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    destino = DIR_PROCESSED / "dicionario_variaveis.csv"
    df.to_csv(destino, index=False, encoding="utf-8")
    print(f"{len(df)} variáveis catalogadas -> {destino}")
    return df


if __name__ == "__main__":
    gerar()
