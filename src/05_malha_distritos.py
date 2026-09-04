"""
Extrai os poligonos dos distritos de Brumadinho da malha do IBGE (shapefile de
MG) e grava um GeoJSON usado pelo mapa do site.

O shapefile do IBGE vem em SIRGAS 2000, que para efeito de desenho equivale a
WGS84 (o padrao que o GeoJSON e o D3 esperam), entao nao ha reprojecao.

Gera:
    data/processed/distritos_brumadinho.geojson
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import shapefile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED, DIR_RAW_MALHA, CD_MUNICIPIO_BRUMADINHO, DISTRITOS_ALVO

NOME_ZIP = "MG_distritos_CD2022.zip"
CASAS_DECIMAIS = 5  # ~1 m; o arquivo original tem precisao muito maior do que um mapa web usa


def _arredondar(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], CASAS_DECIMAIS), round(coords[1], CASAS_DECIMAIS)]
    return [_arredondar(c) for c in coords]


def gerar() -> dict:
    caminho_zip = DIR_RAW_MALHA / NOME_ZIP
    if not caminho_zip.exists():
        raise FileNotFoundError(f"{caminho_zip} nao existe. Rode antes: bash download_censo2022.sh")

    destino_extraido = DIR_RAW_MALHA / "MG_distritos_CD2022"
    if not (destino_extraido / "MG_distritos_CD2022.shp").exists():
        with zipfile.ZipFile(caminho_zip) as zf:
            zf.extractall(destino_extraido)

    sf = shapefile.Reader(str(destino_extraido / "MG_distritos_CD2022"), encoding="utf-8")

    feicoes = []
    for shape_rec in sf.iterShapeRecords():
        registro = shape_rec.record.as_dict()
        if str(registro["CD_MUN"]) != CD_MUNICIPIO_BRUMADINHO:
            continue
        geo = shape_rec.shape.__geo_interface__
        feicoes.append(
            {
                "type": "Feature",
                "properties": {
                    "cd_dist": registro["CD_DIST"],
                    "nm_dist": registro["NM_DIST"],
                    "area_km2": float(registro["AREA_KM2"]),
                    "populacao": int(registro["v0001"]),
                    "domicilios": int(registro["v0002"]),
                    "alvo": registro["CD_DIST"] in DISTRITOS_ALVO,
                },
                "geometry": {"type": geo["type"], "coordinates": _arredondar(geo["coordinates"])},
            }
        )

    feicoes.sort(key=lambda f: f["properties"]["cd_dist"])
    geojson = {"type": "FeatureCollection", "features": feicoes}

    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    destino = DIR_PROCESSED / "distritos_brumadinho.geojson"
    destino.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"{len(feicoes)} distritos -> {destino} ({destino.stat().st_size/1024:.0f} KB)")
    return geojson


if __name__ == "__main__":
    gerar()
