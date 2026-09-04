# -*- coding: utf-8 -*-
"""
03_piramide_etaria.py
======================
Transforma o arquivo largo censo2022_demografia_distritos.csv (uma linha por
distrito, uma coluna por combinação sexo/faixa etária — ex.: V01009 = "Sexo
masculino, 0 a 4 anos") num formato longo (tidy): uma linha por
distrito/sexo/faixa etária. É esse formato que o Power BI usa bem para a
pirâmide etária (eixo de categoria "faixa etária", séries "Masculino"/
"Feminino" com valores espelhados).

Depende de já ter rodado, nessa ordem:
    python src/01_processar_censo.py
    python src/02_gerar_dicionario.py

Gera:
    data/processed/censo2022_piramide_etaria_distritos.csv
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED

ORDEM_FAIXAS = [
    "0 a 4 anos",
    "5 a 9 anos",
    "10 a 14 anos",
    "15 a 19 anos",
    "20 a 24 anos",
    "25 a 29 anos",
    "30 a 39 anos",
    "40 a 49 anos",
    "50 a 59 anos",
    "60 a 69 anos",
    "70 anos ou mais",
]


def _parse_descricao(descricao: str) -> tuple[str, str] | None:
    """'Sexo masculino, 0 a 4 anos' -> ('Masculino', '0 a 4 anos'); '0 a 4
    anos' -> ('Total', '0 a 4 anos'). Retorna None para descrições que não
    são faixa etária (totais agregados, não linhas da pirâmide)."""
    descricao = descricao.strip()

    m = re.match(r"^Sexo masculino,\s*(.+)$", descricao, re.IGNORECASE)
    if m:
        return "Masculino", m.group(1).strip()

    m = re.match(r"^Sexo feminino,\s*(.+)$", descricao, re.IGNORECASE)
    if m:
        return "Feminino", m.group(1).strip()

    if descricao in ORDEM_FAIXAS:
        return "Total", descricao

    return None


def construir() -> pd.DataFrame:
    caminho_demografia = DIR_PROCESSED / "censo2022_demografia_distritos.csv"
    caminho_dicionario = DIR_PROCESSED / "dicionario_variaveis.csv"

    if not caminho_demografia.exists():
        raise FileNotFoundError(f"{caminho_demografia} não existe. Rode antes: python src/01_processar_censo.py")
    if not caminho_dicionario.exists():
        raise FileNotFoundError(f"{caminho_dicionario} não existe. Rode antes: python src/02_gerar_dicionario.py")

    demografia = pd.read_csv(caminho_demografia)
    dicionario = pd.read_csv(caminho_dicionario)

    # Mapa variavel_num -> descrição, só do tema Demografia (evita colisão
    # de números entre temas diferentes)
    dic_demografia = dicionario[dicionario["tema"] == "Demografia"].set_index("variavel_num")["descricao"]

    colunas_id = ["CD_DIST", "NM_DIST", "distrito_alvo"]
    colunas_variaveis = [c for c in demografia.columns if c not in colunas_id]

    linhas = []
    for _, linha in demografia.iterrows():
        for col in colunas_variaveis:
            m = re.match(r"^[Vv](\d+)$", col)
            if not m:
                continue
            num = int(m.group(1))
            descricao = dic_demografia.get(num)
            if descricao is None:
                continue
            parsed = _parse_descricao(descricao)
            if parsed is None:
                continue
            sexo, faixa = parsed
            linhas.append(
                {
                    "CD_DIST": linha["CD_DIST"],
                    "NM_DIST": linha["NM_DIST"],
                    "distrito_alvo": linha["distrito_alvo"],
                    "sexo": sexo,
                    "faixa_etaria": faixa,
                    "populacao": linha[col],
                }
            )

    df = pd.DataFrame(linhas)

    # Ordem "natural" das faixas etárias, não alfabética — ajuda o eixo do
    # gráfico a sair certo sem precisar configurar "ordenar por coluna"
    df["faixa_etaria"] = pd.Categorical(df["faixa_etaria"], categories=ORDEM_FAIXAS, ordered=True)
    df = df.sort_values(["distrito_alvo", "sexo", "faixa_etaria"]).reset_index(drop=True)

    destino = DIR_PROCESSED / "censo2022_piramide_etaria_distritos.csv"
    df.to_csv(destino, index=False, encoding="utf-8")
    print(f"{len(df)} linhas (formato longo) -> {destino}")

    # Checagem simples de consistência: Masculino + Feminino deve bater com
    # o Total por faixa etária
    pivot = df.pivot_table(
        index=["distrito_alvo", "faixa_etaria"],
        columns="sexo",
        values="populacao",
        aggfunc="sum",
        observed=True,
    )
    if {"Masculino", "Feminino", "Total"}.issubset(pivot.columns):
        diverge = (pivot["Masculino"] + pivot["Feminino"] - pivot["Total"]).abs()
        if (diverge > 0).any():
            print("[aviso] Encontrei diferenças entre Masculino+Feminino e Total em algumas faixas — confira manualmente:")
            print(pivot[diverge > 0])
        else:
            print("Checagem OK: Masculino + Feminino = Total em todas as faixas.")

    return df


if __name__ == "__main__":
    construir()
