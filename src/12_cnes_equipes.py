"""
Extrai equipes de saude e profissionais vinculados a elas, por distrito.

Contar predios (o que o 06_cnes_saude.py faz) diz pouco: uma sala de vacina e
um centro de saude contam igual. Equipe e profissional medem capacidade de
atendimento de fato.

A base completa do CNES (BASE_DE_DADOS_CNES_AAAAMM.ZIP, ~700 MB) e lida em
streaming, sem descompactar em disco, e so as linhas de Brumadinho ficam. O
arquivo de dados pessoais dos profissionais (tbDadosProfissionalSus, com nome e
CPF) nao e aberto: a contagem usa o identificador ja anonimizado do vinculo.

O distrito vem do 06_cnes_saude.py, que cruzou coordenada com a malha do IBGE.

Gera:
    data/processed/cnes_equipes_brumadinho.csv
    data/processed/cnes_profissionais_brumadinho.csv
"""

from __future__ import annotations

import csv
import io
import sys
import zipfile
from pathlib import Path

import unicodedata

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import CD_MUNICIPIO_BRUMADINHO, DIR_PROCESSED, DIR_RAW_CNES, DISTRITOS_ALVO

COMPETENCIA = "202607"
NOME_ZIP = f"BASE_DE_DADOS_CNES_{COMPETENCIA}.ZIP"
URL = f"https://cnes.datasus.gov.br/EstatisticasServlet?path={NOME_ZIP}"
CD_MUN_CNES = CD_MUNICIPIO_BRUMADINHO[:6]

POPULACOES_ASSISTIDAS = {
    "TP_POP_ASSIST_QUILOMB": "Quilombola",
    "TP_POP_ASSIST_ASSENT": "Assentamento",
    "TP_POP_ASSIST_GERAL": "Geral",
    "TP_POP_ASSIST_ESCOLA": "Escola",
    "TP_POP_ASSIST_INDIGENA": "Indígena",
    "TP_POP_ASSIST_RIBEIRINHA": "Ribeirinha",
    "TP_POP_ASSIST_SITUACAO_RUA": "População em situação de rua",
}


def _sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in normalizado if not unicodedata.combining(c)).upper().strip()


def _distrito_atendido(referencia: str, distrito_da_sede: str) -> str:
    """Uma equipe atende um distrito se esta sediada nele ou se a area de
    referencia cadastrada tem o nome dele. A segunda regra importa porque a
    equipe com referencia SAO JOSE fica sediada na USF Marinhos, fora do
    distrito de Sao Jose do Paraopeba."""
    ref = _sem_acento(referencia)
    for nome in DISTRITOS_ALVO.values():
        partes = _sem_acento(nome).split()
        if ref == _sem_acento(nome) or (partes and ref == partes[0]) or _sem_acento(nome).startswith(ref):
            return nome
    return distrito_da_sede


def _filtrar(zf: zipfile.ZipFile, nome: str, coluna_filtro: str, valor: str) -> pd.DataFrame:
    with zf.open(nome) as bruto:
        fluxo = csv.reader(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")
        cabecalho = next(fluxo)
        idx = cabecalho.index(coluna_filtro)
        linhas = [linha for linha in fluxo if len(linha) > idx and linha[idx] == valor]
    return pd.DataFrame(linhas, columns=cabecalho)


def _tabela(zf: zipfile.ZipFile, nome: str) -> pd.DataFrame:
    with zf.open(nome) as bruto:
        return pd.read_csv(bruto, sep=";", encoding="latin-1", dtype=str, low_memory=False)


def gerar() -> tuple[pd.DataFrame, pd.DataFrame]:
    caminho = DIR_RAW_CNES / NOME_ZIP
    if not caminho.exists():
        raise FileNotFoundError(
            f"{caminho} nao existe. Baixe com:\n  curl -L -o {caminho} '{URL}'"
        )

    estabelecimentos = pd.read_csv(DIR_PROCESSED / "cnes_estabelecimentos_brumadinho.csv",
                                   dtype={"codigo_cnes": str})
    distrito_por_cnes = dict(zip(estabelecimentos["codigo_cnes"], estabelecimentos["distrito"]))
    nome_por_cnes = dict(zip(estabelecimentos["codigo_cnes"], estabelecimentos["nome_fantasia"]))

    with zipfile.ZipFile(caminho) as zf:
        equipes = _filtrar(zf, f"tbEquipe{COMPETENCIA}.csv", "CO_MUNICIPIO", CD_MUN_CNES)
        vinculos = _filtrar(zf, f"rlEstabEquipeProf{COMPETENCIA}.csv", "CO_MUNICIPIO", CD_MUN_CNES)
        tipos = _tabela(zf, f"tbTipoEquipe{COMPETENCIA}.csv")
        cbos = _tabela(zf, f"tbAtividadeProfissional{COMPETENCIA}.csv")

    # CO_UNIDADE tem 13 digitos: 6 do municipio + 7 do CNES
    def cnes_do_registro(codigo: str) -> str:
        return str(codigo).strip()[-7:].lstrip("0")

    equipes = equipes[equipes["DT_DESATIVACAO"].fillna("").str.strip() == ""].copy()
    equipes["codigo_cnes"] = equipes["CO_UNIDADE"].map(cnes_do_registro)
    equipes["distrito"] = equipes["codigo_cnes"].map(distrito_por_cnes).fillna("não localizado")
    equipes["estabelecimento"] = equipes["codigo_cnes"].map(nome_por_cnes)
    equipes = equipes.merge(tipos[["TP_EQUIPE", "DS_EQUIPE"]], on="TP_EQUIPE", how="left")
    equipes["tipo_equipe"] = equipes["DS_EQUIPE"].fillna("não identificado").str.strip()
    equipes["populacoes_assistidas"] = equipes.apply(
        lambda l: ", ".join(rotulo for col, rotulo in POPULACOES_ASSISTIDAS.items() if str(l.get(col)).strip() == "1"),
        axis=1,
    )

    vinculos = vinculos[vinculos["DT_DESLIGAMENTO"].fillna("").str.strip() == ""].copy()
    vinculos["codigo_cnes"] = vinculos["CO_UNIDADE"].map(cnes_do_registro)
    vinculos["distrito"] = vinculos["codigo_cnes"].map(distrito_por_cnes).fillna("não localizado")
    vinculos = vinculos.merge(cbos[["CO_CBO", "DS_ATIVIDADE_PROFISSIONAL"]], on="CO_CBO", how="left")
    vinculos["ocupacao"] = vinculos["DS_ATIVIDADE_PROFISSIONAL"].fillna("não identificada").str.strip().str.title()
    # Um profissional pode ter mais de um vinculo: para contar pessoas, deduplica
    vinculos = vinculos.drop_duplicates(subset=["CO_PROFISSIONAL_SUS", "codigo_cnes", "CO_CBO"])

    equipes["NO_REFERENCIA"] = equipes["NO_REFERENCIA"].fillna("").str.strip()
    equipes["distrito_atendido"] = equipes.apply(
        lambda l: _distrito_atendido(l["NO_REFERENCIA"], l["distrito"]), axis=1)

    col_equipes = ["codigo_cnes", "estabelecimento", "distrito", "distrito_atendido",
                   "tipo_equipe", "NO_REFERENCIA", "populacoes_assistidas", "DT_ATIVACAO"]
    col_vinculos = ["codigo_cnes", "distrito", "ocupacao", "CO_CBO", "CO_PROFISSIONAL_SUS"]

    destino_eq = DIR_PROCESSED / "cnes_equipes_brumadinho.csv"
    destino_pr = DIR_PROCESSED / "cnes_profissionais_brumadinho.csv"
    equipes[col_equipes].to_csv(destino_eq, index=False, encoding="utf-8")
    vinculos[col_vinculos].to_csv(destino_pr, index=False, encoding="utf-8")

    print(f"{len(equipes)} equipes ativas e {len(vinculos)} vinculos profissionais em Brumadinho")
    print("equipes por distrito da sede:")
    print(equipes.groupby("distrito").size().to_string())
    print("equipes por distrito atendido:")
    print(equipes.groupby("distrito_atendido").size().to_string())
    print(vinculos.groupby("distrito").size().to_string())
    print(f"-> {destino_eq}\n-> {destino_pr}")
    return equipes, vinculos


if __name__ == "__main__":
    gerar()
