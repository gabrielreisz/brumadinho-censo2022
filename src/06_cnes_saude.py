"""
Baixa os estabelecimentos de saude de Brumadinho no CNES (API de dados abertos
do Ministerio da Saude) e descobre em qual distrito cada um esta, cruzando as
coordenadas do estabelecimento com os poligonos da malha do IBGE.

Esse cruzamento e o que torna o dado distrital: o CNES so informa municipio e
bairro, e nome de bairro nao identifica distrito de forma confiavel.

Depende de ter rodado antes 05_malha_distritos.py.

Gera:
    data/processed/cnes_estabelecimentos_brumadinho.csv
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CD_MUNICIPIO_BRUMADINHO, DIR_PROCESSED

API = "https://apidadosabertos.saude.gov.br/cnes"
CD_MUN_CNES = CD_MUNICIPIO_BRUMADINHO[:6]  # o CNES usa o codigo IBGE sem o digito verificador
PAGINA = 20  # limite maximo aceito pela API

CAMPOS = [
    "codigo_cnes",
    "nome_fantasia",
    "nome_razao_social",
    "codigo_tipo_unidade",
    "bairro_estabelecimento",
    "endereco_estabelecimento",
    "numero_telefone_estabelecimento",
    "descricao_turno_atendimento",
    "descricao_esfera_administrativa",
    "estabelecimento_faz_atendimento_ambulatorial_sus",
    "estabelecimento_possui_atendimento_hospitalar",
    "latitude_estabelecimento_decimo_grau",
    "longitude_estabelecimento_decimo_grau",
]


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp)


def baixar_estabelecimentos() -> list[dict]:
    todos, offset = [], 0
    while True:
        pagina = _get(f"{API}/estabelecimentos?codigo_municipio={CD_MUN_CNES}&limit={PAGINA}&offset={offset}")
        lote = pagina.get("estabelecimentos", [])
        if not lote:
            break
        todos.extend(lote)
        offset += PAGINA
        time.sleep(0.2)
    return todos


def baixar_tipos() -> dict[int, str]:
    tipos = _get(f"{API}/tipounidades?limit=100")["tipos_unidade"]
    return {t["codigo_tipo_unidade"]: t["descricao_tipo_unidade"] for t in tipos}


def _ponto_no_anel(lon: float, lat: float, anel: list) -> bool:
    """Ray casting: conta quantas vezes uma semirreta horizontal cruza o anel."""
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


def localizar_distrito(lon: float | None, lat: float | None, distritos: list[dict]) -> str:
    if lon is None or lat is None:
        return "sem coordenada"
    for feicao in distritos:
        if _ponto_no_poligono(lon, lat, feicao["geometry"]):
            return feicao["properties"]["nm_dist"]
    return "fora dos limites do municipio"


def gerar() -> pd.DataFrame:
    caminho_geojson = DIR_PROCESSED / "distritos_brumadinho.geojson"
    if not caminho_geojson.exists():
        raise FileNotFoundError(f"{caminho_geojson} nao existe. Rode antes: python src/05_malha_distritos.py")
    distritos = json.loads(caminho_geojson.read_text(encoding="utf-8"))["features"]

    estabelecimentos = baixar_estabelecimentos()
    tipos = baixar_tipos()
    print(f"{len(estabelecimentos)} estabelecimentos no CNES para Brumadinho")

    linhas = []
    for e in estabelecimentos:
        lat = e.get("latitude_estabelecimento_decimo_grau")
        lon = e.get("longitude_estabelecimento_decimo_grau")
        linha = {c: e.get(c) for c in CAMPOS}
        linha["descricao_tipo_unidade"] = tipos.get(e.get("codigo_tipo_unidade"), "nao identificado")
        linha["distrito"] = localizar_distrito(lon, lat, distritos)
        linhas.append(linha)

    df = pd.DataFrame(linhas)
    destino = DIR_PROCESSED / "cnes_estabelecimentos_brumadinho.csv"
    df.to_csv(destino, index=False, encoding="utf-8")
    print(df["distrito"].value_counts().to_string())
    print(f"-> {destino}")
    return df


if __name__ == "__main__":
    gerar()
