"""
Recorta o Censo 2010 (agregados por setor censitario) para os distritos-alvo,
para comparar com 2022.

Duas coisas so existem aqui:
  - serie historica: saneamento em 2010 x 2022, para ver se a diferenca entre
    os distritos aumentou ou diminuiu;
  - renda: em 2010 o IBGE publicou rendimento por setor censitario, o que
    permite chegar ao distrito. Em 2022 isso saiu do universo e foi para a
    amostra, publicada so ate municipio - por isso a renda do painel e de 2010.

O arquivo Basico traz Cod_distrito, entao o recorte e por codigo, sem
cruzamento geografico.

Gera:
    data/processed/censo2010_distritos.csv
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED, DIR_RAW_CENSO2010, DISTRITOS_ALVO

NOME_ZIP = "MG_20260615.zip"

# Variaveis do Censo 2010 (documentacao "Agregado dos Setores 2010", secoes 6.2 e 6.19).
# Atencao: as categorias de 2010 sao mais agregadas que as de 2022 - so os tres
# indicadores abaixo tem definicao equivalente nos dois censos.
DOMICILIO01 = {
    "domicilios_permanentes": ["V002"],
    "agua_rede_geral": ["V012"],
    "esgoto_rede_geral": ["V017"],
    "lixo_coletado": ["V035"],
}
DOMICILIO_RENDA = {
    "ate_1_8_sm": "V005", "1_8_a_1_4_sm": "V006", "1_4_a_1_2_sm": "V007",
    "1_2_a_1_sm": "V008", "1_a_2_sm": "V009", "2_a_3_sm": "V010",
    "3_a_5_sm": "V011", "5_a_10_sm": "V012", "mais_10_sm": "V013",
    "sem_rendimento": "V014",
}
ROTULOS_RENDA = {
    "ate_1_8_sm": "Até 1/8 SM", "1_8_a_1_4_sm": "1/8 a 1/4 SM", "1_4_a_1_2_sm": "1/4 a 1/2 SM",
    "1_2_a_1_sm": "1/2 a 1 SM", "1_a_2_sm": "1 a 2 SM", "2_a_3_sm": "2 a 3 SM",
    "3_a_5_sm": "3 a 5 SM", "5_a_10_sm": "5 a 10 SM", "mais_10_sm": "Mais de 10 SM",
    "sem_rendimento": "Sem rendimento",
}


def _ler(zf: zipfile.ZipFile, nome: str) -> pd.DataFrame:
    caminho = next(n for n in zf.namelist() if n.endswith(f"/CSV/{nome}"))
    with zf.open(caminho) as f:
        return pd.read_csv(f, sep=";", encoding="latin1", low_memory=False, dtype=str)


def _somar(df: pd.DataFrame, colunas: list[str]) -> float:
    total = 0.0
    for c in colunas:
        serie = pd.to_numeric(df[c].astype(str).str.replace(",", "."), errors="coerce")
        total += serie.fillna(0).sum()
    return float(total)


def gerar() -> pd.DataFrame:
    caminho = DIR_RAW_CENSO2010 / NOME_ZIP
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho} nao existe. Rode antes: bash download_censo2022.sh")

    with zipfile.ZipFile(caminho) as zf:
        basico = _ler(zf, "Basico_MG.csv")
        basico["Cod_distrito"] = basico["Cod_distrito"].astype(str).str.strip()
        basico = basico[basico["Cod_distrito"].isin(DISTRITOS_ALVO)]
        setores = dict(zip(basico["Cod_setor"].astype(str).str.strip(), basico["Cod_distrito"]))
        print(f"{len(setores)} setores censitarios de 2010 nos dois distritos")

        dom01 = _ler(zf, "Domicilio01_MG.csv")
        renda = _ler(zf, "DomicilioRenda_MG.csv")

    linhas = []
    for cd_dist, nome in DISTRITOS_ALVO.items():
        codigos = {s for s, d in setores.items() if d == cd_dist}
        sub_basico = basico[basico["Cod_setor"].astype(str).str.strip().isin(codigos)]
        sub01 = dom01[dom01["Cod_setor"].astype(str).str.strip().isin(codigos)]
        sub_renda = renda[renda["Cod_setor"].astype(str).str.strip().isin(codigos)]

        registro = {"distrito": nome, "cd_dist": cd_dist, "ano": 2010,
                    "populacao": _somar(sub_basico, ["V002"])}
        for chave, cols in DOMICILIO01.items():
            registro[chave] = _somar(sub01, cols)
        for chave, coluna in DOMICILIO_RENDA.items():
            registro[f"renda_{chave}"] = _somar(sub_renda, [coluna])
        linhas.append(registro)

    df = pd.DataFrame(linhas)
    for chave in ["agua_rede_geral", "esgoto_rede_geral", "lixo_coletado"]:
        df[f"pct_{chave}"] = 100 * df[chave] / df["domicilios_permanentes"]

    destino = DIR_PROCESSED / "censo2010_distritos.csv"
    df.to_csv(destino, index=False, encoding="utf-8")
    print(df[["distrito", "populacao", "domicilios_permanentes",
              "pct_agua_rede_geral", "pct_esgoto_rede_geral", "pct_lixo_coletado"]].round(1).to_string(index=False))
    print(f"-> {destino}")
    return df


if __name__ == "__main__":
    gerar()
