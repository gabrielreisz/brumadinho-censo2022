"""
Recorta o Cadastro Nacional de Barragens de Mineracao (ANM) para Brumadinho e
descobre em qual distrito cada barragem esta.

O cadastro da municipio, nao distrito, entao vale o mesmo cruzamento
geografico usado no CNES: coordenada contra os poligonos da malha do IBGE.
As coordenadas vem em grau-minuto-segundo e sao convertidas para decimal.

A barragem B1 da Mina Corrego do Feijao, que rompeu em 25/01/2019, nao esta no
cadastro: o que aparece sao as estruturas remanescentes da mesma mina.

Depende de ter rodado antes 05_malha_distritos.py.

Gera:
    data/processed/anm_barragens_brumadinho.csv
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED, DIR_RAW_ANM

NOME_ARQUIVO = "Barragens.csv"
URL = "https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv"

COLUNAS = {
    "Nome": "nome",
    "Empreendedor": "empreendedor",
    "Nome da mina": "mina",
    "Categoria de Risco - CRI": "risco",
    "Dano Potencial Associado - DPA": "dano_potencial",
    "Nível de Emergência": "nivel_emergencia",
    "Situação Operacional": "situacao",
    "Método construtivo da barragem": "metodo_construtivo",
    "Altura máxima atual (m)": "altura_m",
    "Volume atual do Reservatório (m³)": "volume_m3",
    "Existência de população a jusante": "populacao_jusante",
    "Número de pessoas possivelmente afetadas a jusante em caso de rompimento da barragem": "pessoas_jusante",
    "Minério principal presente no reservatório": "minerio",
}


def _para_decimal(texto: str) -> float | None:
    """'-20°07'41.100''' -> -20.128083"""
    if not isinstance(texto, str):
        return None
    m = re.match(r"^\s*(-?)(\d+)°\s*(\d+)'\s*([\d.]+)", texto.strip())
    if not m:
        return None
    sinal, grau, minuto, segundo = m.groups()
    valor = int(grau) + int(minuto) / 60 + float(segundo) / 3600
    return -valor if sinal == "-" else valor


def _ponto_no_anel(lon: float, lat: float, anel: list) -> bool:
    dentro = False
    j = len(anel) - 1
    for i in range(len(anel)):
        xi, yi = anel[i]
        xj, yj = anel[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def _ponto_no_poligono(lon: float, lat: float, geometria: dict) -> bool:
    poligonos = geometria["coordinates"] if geometria["type"] == "MultiPolygon" else [geometria["coordinates"]]
    for poligono in poligonos:
        if _ponto_no_anel(lon, lat, poligono[0]) and not any(
            _ponto_no_anel(lon, lat, buraco) for buraco in poligono[1:]
        ):
            return True
    return False


def gerar() -> pd.DataFrame:
    caminho = DIR_RAW_ANM / NOME_ARQUIVO
    if not caminho.exists():
        raise FileNotFoundError(
            f"{caminho} nao existe. Baixe com (o servidor recusa requisicao sem User-Agent de navegador):\n"
            f"  curl -L -H 'User-Agent: Mozilla/5.0' -o {caminho} '{URL}'"
        )

    caminho_geojson = DIR_PROCESSED / "distritos_brumadinho.geojson"
    if not caminho_geojson.exists():
        raise FileNotFoundError(f"{caminho_geojson} nao existe. Rode antes: python src/05_malha_distritos.py")
    distritos = json.loads(caminho_geojson.read_text(encoding="utf-8"))["features"]

    df = pd.read_csv(caminho, encoding="latin-1", dtype=str)
    df = df[df["Município"].astype(str).str.upper().str.strip() == "BRUMADINHO"].copy()

    df["lat"] = df["Latitude"].map(_para_decimal)
    df["lon"] = df["Longitude"].map(_para_decimal)

    def localizar(linha) -> str:
        if pd.isna(linha["lat"]) or pd.isna(linha["lon"]):
            return "sem coordenada"
        for feicao in distritos:
            if _ponto_no_poligono(linha["lon"], linha["lat"], feicao["geometry"]):
                return feicao["properties"]["nm_dist"]
        return "fora dos limites do municipio"

    df["distrito"] = df.apply(localizar, axis=1)
    saida = df[["lat", "lon", "distrito"] + list(COLUNAS)].rename(columns=COLUNAS)
    saida["pessoas_jusante"] = pd.to_numeric(saida["pessoas_jusante"], errors="coerce")
    saida = saida.sort_values(["distrito", "nivel_emergencia", "nome"])

    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    destino = DIR_PROCESSED / "anm_barragens_brumadinho.csv"
    saida.to_csv(destino, index=False, encoding="utf-8")

    print(f"{len(saida)} barragens de mineracao em Brumadinho")
    print(saida.groupby(["distrito", "nivel_emergencia"]).size().to_string())
    print(f"-> {destino}")
    return saida


if __name__ == "__main__":
    gerar()
