"""
Recorta os setores censitarios dos distritos-alvo e junta malha + indicadores,
para o mapa de calor dentro de cada distrito.

O distrito e o menor nivel que o IBGE publica pre-agregado, mas o setor
censitario e mais fino ainda: da pra ver desigualdade dentro do mesmo distrito.
O codigo do setor (15 digitos) comeca com o codigo do distrito (9 digitos), o
que dispensa cruzamento geografico.

Gera:
    data/processed/setores_distritos.geojson   (poligonos + indicadores)
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pandas as pd
import shapefile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED, DIR_RAW_SETORES, DISTRITOS_ALVO

NOME_MALHA = "MG_setores_CD2022"
CASAS_DECIMAIS = 5

ARQUIVOS_TEMA = {
    "basico": "Agregados_por_setores_basico_BR_20260520.zip",
    "domicilio2": "Agregados_por_setores_caracteristicas_domicilio2_BR_20250417.zip",
}

# Indicadores calculados por setor. Cada um vira uma camada do mapa de calor.
# numerador / denominador, ambos como listas de variaveis a somar.
INDICADORES = {
    "esgoto_rede": {
        "rotulo": "Esgoto em rede geral ou pluvial",
        "tema": "domicilio2",
        "numerador": ["V00309", "V00310"],
        "denominador": [f"V{n:05d}" for n in range(309, 317)],
    },
    "agua_rede": {
        "rotulo": "Água da rede geral",
        "tema": "domicilio2",
        "numerador": ["V00111"],
        "denominador": [f"V{n:05d}" for n in range(111, 119)],
    },
    "lixo_coletado": {
        "rotulo": "Lixo coletado por serviço de limpeza",
        "tema": "domicilio2",
        "numerador": ["V00397", "V00398"],
        "denominador": [f"V{n:05d}" for n in range(397, 403)],
    },
}


def _arredondar(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], CASAS_DECIMAIS), round(coords[1], CASAS_DECIMAIS)]
    return [_arredondar(c) for c in coords]


def _ler_tema(nome_zip: str, setores_alvo: set[str]) -> pd.DataFrame:
    caminho = DIR_RAW_SETORES / nome_zip
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho} nao existe. Rode antes: bash download_censo2022.sh")
    with zipfile.ZipFile(caminho) as zf:
        nome_csv = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(nome_csv) as f:
            df = pd.read_csv(f, sep=";", encoding="latin1", low_memory=False, dtype={"CD_SETOR": str})
    coluna = "CD_SETOR" if "CD_SETOR" in df.columns else df.columns[0]
    df[coluna] = df[coluna].astype(str).str.strip()
    return df[df[coluna].isin(setores_alvo)].set_index(coluna)


def _valor(linha: pd.Series, colunas: list[str]) -> float:
    total = 0.0
    for c in colunas:
        bruto = linha.get(c)
        if bruto is None or (isinstance(bruto, float) and pd.isna(bruto)):
            continue
        if isinstance(bruto, str):
            bruto = bruto.replace(".", "").replace(",", ".")
            if not bruto.strip() or bruto.strip() in {"X", "-"}:
                continue
        total += float(bruto)
    return total


def gerar() -> dict:
    caminho_zip = DIR_RAW_SETORES / f"{NOME_MALHA}.zip"
    if not caminho_zip.exists():
        raise FileNotFoundError(f"{caminho_zip} nao existe. Rode antes: bash download_censo2022.sh")

    extraido = DIR_RAW_SETORES / NOME_MALHA
    if not (extraido / f"{NOME_MALHA}.shp").exists():
        with zipfile.ZipFile(caminho_zip) as zf:
            zf.extractall(extraido)

    sf = shapefile.Reader(str(extraido / NOME_MALHA), encoding="utf-8")
    feicoes = []
    for shape_rec in sf.iterShapeRecords():
        registro = shape_rec.record.as_dict()
        cd_dist = str(registro.get("CD_DIST", ""))
        if cd_dist not in DISTRITOS_ALVO:
            continue
        geo = shape_rec.shape.__geo_interface__
        feicoes.append({
            "cd_setor": str(registro["CD_SETOR"]),
            "distrito": DISTRITOS_ALVO[cd_dist],
            "situacao": registro.get("SITUACAO", ""),
            "area_km2": float(registro.get("AREA_KM2") or 0),
            "geometry": {"type": geo["type"], "coordinates": _arredondar(geo["coordinates"])},
        })

    setores_alvo = {f["cd_setor"] for f in feicoes}
    print(f"{len(feicoes)} setores censitarios nos dois distritos")

    temas = {nome: _ler_tema(arq, setores_alvo) for nome, arq in ARQUIVOS_TEMA.items()}
    basico = temas["basico"]

    saida = []
    for f in feicoes:
        setor = f["cd_setor"]
        propriedades = {
            "cd_setor": setor,
            "distrito": f["distrito"],
            "situacao": f["situacao"],
            "area_km2": f["area_km2"],
        }
        if setor in basico.index:
            linha = basico.loc[setor]
            propriedades["populacao"] = _valor(linha, ["v0001"]) or _valor(linha, ["V0001"])
            propriedades["domicilios"] = _valor(linha, ["v0007"]) or _valor(linha, ["V0007"])

        for chave, cfg in INDICADORES.items():
            tabela = temas[cfg["tema"]]
            if setor not in tabela.index:
                propriedades[chave] = None
                continue
            linha = tabela.loc[setor]
            denominador = _valor(linha, cfg["denominador"])
            propriedades[chave] = 100 * _valor(linha, cfg["numerador"]) / denominador if denominador else None

        saida.append({"type": "Feature", "properties": propriedades, "geometry": f["geometry"]})

    geojson = {
        "type": "FeatureCollection",
        "indicadores": {k: v["rotulo"] for k, v in INDICADORES.items()},
        "features": saida,
    }
    destino = DIR_PROCESSED / "setores_distritos.geojson"
    destino.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"-> {destino} ({destino.stat().st_size/1024:.0f} KB)")

    resumo = pd.DataFrame([f["properties"] for f in saida])
    print(resumo.groupby("distrito")[["populacao", "esgoto_rede", "agua_rede", "lixo_coletado"]]
          .agg({"populacao": "sum", "esgoto_rede": "mean", "agua_rede": "mean", "lixo_coletado": "mean"}).round(1).to_string())
    return geojson


if __name__ == "__main__":
    gerar()
