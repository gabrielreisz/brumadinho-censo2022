"""
Filtra as bases do DataViva (Cedeplar/UFMG, construidas a partir da RAIS) para
o municipio de Brumadinho.

Os arquivos do DataViva cobrem o Brasil inteiro e tem centenas de MB, entao o
download e feito em streaming: cada linha e testada na hora e so as de
Brumadinho ficam em memoria. Como os arquivos vem ordenados por codigo de
municipio, a leitura para assim que o codigo passa do de Brumadinho.

Atencao ao nivel geografico: DataViva/RAIS nao desce abaixo de municipio.
Estes dados sao contexto municipal, nao dos distritos.

Gera, em data/processed/:
    dataviva_emprego_cnae_brumadinho.csv
    dataviva_emprego_escolaridade_brumadinho.csv
    dataviva_salario_sexo_raca_brumadinho.csv
    dataviva_salario_escolaridade_brumadinho.csv
"""

from __future__ import annotations

import csv
import io
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CD_MUNICIPIO_BRUMADINHO, DIR_PROCESSED

BASE = "https://dvp-stg-site.s3.us-east-2.amazonaws.com/downloads"
CD_MUN_RAIS = CD_MUNICIPIO_BRUMADINHO[:6]  # a RAIS usa o codigo IBGE sem o digito verificador
COLUNA_MUNICIPIO = "Código IBGE"

ARQUIVOS = {
    "dataviva_emprego_cnae_brumadinho.csv": "Emprego/CNAE/emprego_cnae_municipio_2024.csv",
    "dataviva_emprego_escolaridade_brumadinho.csv": "Emprego/escolaridade/emprego_escolaridade_municipio_2024.csv",
    "dataviva_salario_sexo_raca_brumadinho.csv": "Salario_Real/sexo_raca_cor/salario_real_sexo_raca_cor_municipio_2024.csv",
    "dataviva_salario_escolaridade_brumadinho.csv": "Salario_Real/escolaridade/salario_real_escolaridade_municipio_2024.csv",
}


def filtrar(url: str, destino: Path) -> int:
    req = urllib.request.Request(url, headers={"accept-encoding": "identity"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        fluxo = csv.reader(io.TextIOWrapper(resp, encoding="utf-8-sig", newline=""))
        cabecalho = next(fluxo)
        idx = cabecalho.index(COLUNA_MUNICIPIO)

        linhas, achou = [], False
        for linha in fluxo:
            codigo = linha[idx].strip()
            if codigo == CD_MUN_RAIS:
                linhas.append(linha)
                achou = True
            elif achou:
                break  # arquivo ordenado por municipio: passou de Brumadinho, acabou

    with destino.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
    return len(linhas)


def gerar() -> None:
    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    for nome_destino, caminho in ARQUIVOS.items():
        destino = DIR_PROCESSED / nome_destino
        print(f"baixando e filtrando {caminho} ...")
        n = filtrar(f"{BASE}/{caminho}", destino)
        print(f"  {n} linhas de Brumadinho -> {destino.name}")


if __name__ == "__main__":
    gerar()
