"""
Consolida os CSVs tratados num unico JSON que o site (site/) le com D3.

O site e estatico: nao ha backend, entao todo recorte e calculo de percentual
que dependeria de codigo servidor e feito aqui.

Depende de ter rodado antes os scripts 01 a 07.

Gera:
    site/dados/indicadores.json
    site/dados/distritos.geojson
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED, DISTRITOS_ALVO, RAIZ

DIR_SITE_DADOS = RAIZ / "site" / "dados"
DISTRITOS = list(DISTRITOS_ALVO.values())

FAIXAS_PIRAMIDE = [
    "0 a 4 anos", "5 a 9 anos", "10 a 14 anos", "15 a 19 anos", "20 a 24 anos",
    "25 a 29 anos", "30 a 39 anos", "40 a 49 anos", "50 a 59 anos",
    "60 a 69 anos", "70 anos ou mais",
]

SECOES_CNAE = {
    "A": "Agropecuária", "B": "Indústrias extrativas", "C": "Indústrias de transformação",
    "D": "Eletricidade e gás", "E": "Água, esgoto e resíduos", "F": "Construção",
    "G": "Comércio e reparação", "H": "Transporte e armazenagem",
    "I": "Alojamento e alimentação", "J": "Informação e comunicação",
    "K": "Atividades financeiras", "L": "Atividades imobiliárias",
    "M": "Atividades profissionais e técnicas", "N": "Atividades administrativas",
    "O": "Administração pública", "P": "Educação", "Q": "Saúde humana e serviço social",
    "R": "Artes, cultura e esporte", "S": "Outras atividades de serviços",
    "T": "Serviços domésticos", "U": "Organismos internacionais",
}


def _carregar(tema: str) -> pd.DataFrame:
    return pd.read_csv(DIR_PROCESSED / f"censo2022_{tema}_distritos.csv").set_index("distrito_alvo")


def _num(df: pd.DataFrame, distrito: str, coluna: str) -> float:
    """O IBGE grava alguns decimais com virgula, que o pandas le como texto."""
    bruto = df.loc[distrito, coluna]
    if isinstance(bruto, str):
        bruto = bruto.replace(".", "").replace(",", ".")
    return float(bruto)


def _series(df: pd.DataFrame, distrito: str, colunas: dict[str, str]) -> list[dict]:
    """Transforma {variavel: rotulo} numa lista [{rotulo, valor, pct}]."""
    valores = [(rotulo, _num(df, distrito, col)) for col, rotulo in colunas.items()]
    total = sum(v for _, v in valores) or 1
    return [{"rotulo": r, "valor": v, "pct": 100 * v / total} for r, v in valores]


def resumo(distrito: str) -> dict:
    basico = _carregar("basico")
    populacao = _num(basico, distrito, "v0001")
    area = _num(basico, distrito, "AREA_KM2")
    return {
        "populacao": populacao,
        "domicilios": _num(basico, distrito, "v0002"),
        "domicilios_ocupados": _num(basico, distrito, "v0007"),
        "area_km2": area,
        "densidade": populacao / area,
        "media_moradores": _num(basico, distrito, "v0005"),
    }


def piramide(distrito: str) -> list[dict]:
    df = pd.read_csv(DIR_PROCESSED / "censo2022_piramide_etaria_distritos.csv")
    df = df[df["distrito_alvo"] == distrito]
    pivot = df.pivot_table(index="faixa_etaria", columns="sexo", values="populacao", aggfunc="sum")
    pivot = pivot.reindex(FAIXAS_PIRAMIDE).fillna(0)
    return [
        {"faixa": faixa, "homens": float(linha.get("Masculino", 0)), "mulheres": float(linha.get("Feminino", 0))}
        for faixa, linha in pivot.iterrows()
    ]


def cor_raca(distrito: str) -> list[dict]:
    return _series(_carregar("cor_ou_raca"), distrito, {
        "V01317": "Branca", "V01318": "Preta", "V01319": "Amarela",
        "V01320": "Parda", "V01321": "Indígena",
    })


def cor_raca_responsavel(distrito: str) -> list[dict]:
    """Cor/raca de quem responde pelo domicilio. Vem do arquivo de obitos porque
    e la que o IBGE publica essa abertura por distrito; somar 'existe' e 'nao
    existe pessoa falecida' devolve o total de domicilios de cada categoria."""
    df = _carregar("obitos")
    pares = {
        "Branca": ("V01254", "V01255"), "Preta": ("V01256", "V01257"),
        "Amarela": ("V01258", "V01259"), "Parda": ("V01260", "V01261"),
        "Indígena": ("V01262", "V01263"),
    }
    valores = [(rotulo, _num(df, distrito, a) + _num(df, distrito, b)) for rotulo, (a, b) in pares.items()]
    total = sum(v for _, v in valores) or 1
    return [{"rotulo": r, "valor": v, "pct": 100 * v / total} for r, v in valores]


def alfabetizacao(distrito: str) -> dict:
    df = _carregar("alfabetizacao")
    faixas = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49",
              "50-54", "55-59", "60-64", "65-69", "70-79", "80+"]
    cols_total = [f"V{n:05d}" for n in range(644, 657)]
    cols_alfab = [f"V{n:05d}" for n in range(748, 761)]
    por_idade = []
    for faixa, ct, ca in zip(faixas, cols_total, cols_alfab):
        total = _num(df, distrito, ct)
        alfab = _num(df, distrito, ca)
        por_idade.append({"faixa": faixa, "total": total, "alfabetizados": alfab,
                          "taxa": 100 * alfab / total if total else None})
    return {
        "alfabetizados": _num(df, distrito, "V00900"),
        "nao_alfabetizados": _num(df, distrito, "V00901"),
        "por_idade": por_idade,
    }


def saneamento(distrito: str) -> dict:
    dom2 = _carregar("caracteristicas_domicilio2")
    banheiro_com = _num(dom2, distrito, "V00494")
    banheiro_sem = _num(dom2, distrito, "V00495")
    return {
        "agua": _series(dom2, distrito, {
            "V00111": "Rede geral", "V00112": "Poço profundo/artesiano",
            "V00113": "Poço raso/cacimba", "V00114": "Fonte/nascente",
            "V00115": "Carro-pipa", "V00116": "Água da chuva",
            "V00117": "Rios/açudes/córregos", "V00118": "Outra forma",
        }),
        "esgoto": _series(dom2, distrito, {
            "V00309": "Rede geral/pluvial", "V00310": "Fossa séptica ligada à rede",
            "V00311": "Fossa séptica não ligada", "V00312": "Fossa rudimentar/buraco",
            "V00313": "Vala", "V00314": "Rio/lago/córrego", "V00315": "Outra forma",
            "V00316": "Sem banheiro/sanitário",
        }),
        "lixo": _series(dom2, distrito, {
            "V00397": "Coletado por serviço de limpeza", "V00398": "Depositado em caçamba",
            "V00399": "Queimado na propriedade", "V00400": "Enterrado na propriedade",
            "V00401": "Terreno baldio/encosta", "V00402": "Outro destino",
        }),
        "banheiro": {"com": banheiro_com, "sem": banheiro_sem,
                     "pct_com": 100 * banheiro_com / (banheiro_com + banheiro_sem)},
    }


def domicilios(distrito: str) -> dict:
    dom1 = _carregar("caracteristicas_domicilio1")
    especie = _series(dom1, distrito, {
        "V00047": "Casa", "V00048": "Casa de vila/condomínio", "V00049": "Apartamento",
        "V00050": "Cômodos/cortiço", "V00052": "Estrutura degradada",
    })
    moradores = _series(dom1, distrito, {
        "V00017": "1", "V00018": "2", "V00019": "3", "V00020": "4", "V00021": "5",
        "V00022": "6", "V00023": "7", "V00024": "8", "V00025": "9", "V00026": "10+",
    })
    composicao = _series(_carregar("parentesco"), distrito, {
        "V01209": "Unipessoal", "V01210": "Nuclear", "V01211": "Estendida", "V01212": "Composta",
    })
    return {"especie": especie, "moradores": moradores, "composicao": composicao}


def obitos(distrito: str) -> dict:
    """Obitos de moradores entre jan/2019 e jul/2022, como declarado no Censo."""
    df = _carregar("obitos")
    faixas = ["Menos de 1 ano", "1 a 4 anos", "5 a 14 anos", "15 a 19 anos", "20 a 24 anos",
              "25 a 29 anos", "30 a 39 anos", "40 a 49 anos", "50 a 59 anos",
              "60 a 69 anos", "70 anos ou mais"]
    cols_h = [f"V{n:05d}" for n in range(1228, 1239)]
    cols_m = [f"V{n:05d}" for n in range(1239, 1250)]
    por_idade = [
        {"faixa": f, "homens": _num(df, distrito, ch), "mulheres": _num(df, distrito, cm)}
        for f, ch, cm in zip(faixas, cols_h, cols_m)
    ]
    periodos = {
        "V01264": "1º sem. 2019", "V01265": "2º sem. 2019", "V01266": "1º sem. 2020",
        "V01267": "2º sem. 2020", "V01268": "1º sem. 2021", "V01269": "2º sem. 2021",
        "V01270": "jan–jul 2022",
    }
    return {
        "domicilios_com_obito": _num(df, distrito, "V01224"),
        "domicilios_sem_obito": _num(df, distrito, "V01225"),
        "homens": _num(df, distrito, "V01226"),
        "mulheres": _num(df, distrito, "V01227"),
        "por_idade": por_idade,
        "por_periodo": [{"periodo": r, "valor": _num(df, distrito, c)} for c, r in periodos.items()],
    }


def quilombolas(distrito: str) -> dict:
    pessoas = _carregar("pessoas_quilombolas")
    return {
        "total": _num(pessoas, distrito, "V03196"),
        "homens": _num(pessoas, distrito, "V03197"),
        "mulheres": _num(pessoas, distrito, "V03198"),
        "por_idade": [
            {"faixa": "0 a 14 anos", "valor": _num(pessoas, distrito, "V03202")},
            {"faixa": "15 a 29 anos", "valor": _num(pessoas, distrito, "V03203")},
            {"faixa": "30 a 59 anos", "valor": _num(pessoas, distrito, "V03200")},
            {"faixa": "60 anos ou mais", "valor": _num(pessoas, distrito, "V03201")},
        ],
    }


def saude_cnes() -> dict:
    df = pd.read_csv(DIR_PROCESSED / "cnes_estabelecimentos_brumadinho.csv")
    df["sus"] = df["estabelecimento_faz_atendimento_ambulatorial_sus"] == "SIM"
    por_distrito = {}
    for distrito in df["distrito"].unique():
        sub = df[df["distrito"] == distrito]
        por_distrito[distrito] = {
            "total": int(len(sub)),
            "sus": int(sub["sus"].sum()),
            "por_tipo": sub["descricao_tipo_unidade"].value_counts().to_dict(),
            "unidades_basicas": sub[sub["descricao_tipo_unidade"] == "CENTRO DE SAUDE/UNIDADE BASICA"]
            [["nome_fantasia", "bairro_estabelecimento"]].to_dict("records"),
        }
    pontos = df.dropna(subset=["latitude_estabelecimento_decimo_grau"])
    return {
        "por_distrito": por_distrito,
        "pontos": [
            {
                "nome": r["nome_fantasia"],
                "tipo": r["descricao_tipo_unidade"],
                "distrito": r["distrito"],
                "sus": bool(r["sus"]),
                "lat": r["latitude_estabelecimento_decimo_grau"],
                "lon": r["longitude_estabelecimento_decimo_grau"],
            }
            for _, r in pontos.iterrows()
        ],
    }


def contexto_municipal() -> dict:
    emprego = pd.read_csv(DIR_PROCESSED / "dataviva_emprego_cnae_brumadinho.csv")
    emprego = emprego[emprego["Sexo e Raça/Cor"].isin(["BrAm - Total", "Homem - Total", "Mulher - Total"])]
    por_secao = (
        emprego.groupby("Seção CNAE (1 dígito)")["Valor"].sum().sort_values(ascending=False)
    )
    total_empregos = por_secao.sum()

    esc = pd.read_csv(DIR_PROCESSED / "dataviva_salario_escolaridade_brumadinho.csv")
    esc = esc[esc["Indicador"] == "Média do Salário Real"]
    ordem_esc = ["Fundamental Incompleto", "Fundamental Completo", "Médio Completo", "Superior Completo"]

    sexo_raca = pd.read_csv(DIR_PROCESSED / "dataviva_salario_sexo_raca_brumadinho.csv")
    sexo_raca = sexo_raca[sexo_raca["Indicador"] == "Média do Salário Real"]

    emprego_esc = pd.read_csv(DIR_PROCESSED / "dataviva_emprego_escolaridade_brumadinho.csv")
    emprego_esc = emprego_esc[emprego_esc["Indicador"] == "Número de Vínculos"]

    return {
        "emprego_por_secao": [
            {"secao": s, "nome": SECOES_CNAE.get(s, s), "valor": float(v), "pct": 100 * v / total_empregos}
            for s, v in por_secao.items()
        ],
        "total_empregos": float(total_empregos),
        "salario_por_escolaridade": [
            {"escolaridade": e, "valor": float(esc[esc["Abertura"] == e]["Valor"].iloc[0])}
            for e in ordem_esc if (esc["Abertura"] == e).any()
        ],
        "vinculos_por_escolaridade": [
            {"escolaridade": e, "valor": float(emprego_esc[emprego_esc["Abertura"] == e]["Valor"].sum())}
            for e in ordem_esc
        ],
        "salario_por_sexo_raca": [
            {"grupo": g, "valor": float(sexo_raca[sexo_raca["Abertura"] == g]["Valor"].iloc[0])}
            for g in ["Homem - BrAm", "Homem - PPI", "Mulher - BrAm", "Mulher - PPI"]
            if (sexo_raca["Abertura"] == g).any()
        ],
        "indicadores_ibge": [
            {"rotulo": "PIB per capita", "valor": "R$ 73.117", "fonte": "IBGE/Atlas Brasil, 2023"},
            {"rotulo": "Renda per capita até 1/2 salário mínimo", "valor": "33,5%", "fonte": "IBGE, Censo 2010"},
            {"rotulo": "Mortalidade infantil", "valor": "18,1 ‰", "fonte": "IBGE, 2025"},
            {"rotulo": "Esgotamento sanitário adequado", "valor": "53,3%", "fonte": "IBGE, 2022"},
            {"rotulo": "IDHM", "valor": "0,747", "fonte": "IBGE/Atlas Brasil, 2010"},
        ],
    }


def gerar() -> dict:
    saude = saude_cnes()
    dados = {
        "distritos": DISTRITOS,
        "por_distrito": {
            d: {
                "resumo": resumo(d),
                "piramide": piramide(d),
                "cor_raca": cor_raca(d),
                "cor_raca_responsavel": cor_raca_responsavel(d),
                "alfabetizacao": alfabetizacao(d),
                "saneamento": saneamento(d),
                "domicilios": domicilios(d),
                "obitos": obitos(d),
                "quilombolas": quilombolas(d),
                "saude": saude["por_distrito"].get(d, {"total": 0, "sus": 0, "por_tipo": {}, "unidades_basicas": []}),
            }
            for d in DISTRITOS
        },
        "saude_pontos": saude["pontos"],
        "saude_municipio": saude["por_distrito"],
        "municipio": contexto_municipal(),
    }

    DIR_SITE_DADOS.mkdir(parents=True, exist_ok=True)
    destino = DIR_SITE_DADOS / "indicadores.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    shutil.copy(DIR_PROCESSED / "distritos_brumadinho.geojson", DIR_SITE_DADOS / "distritos.geojson")
    print(f"-> {destino} ({destino.stat().st_size/1024:.0f} KB)")
    print(f"-> {DIR_SITE_DADOS / 'distritos.geojson'}")
    return dados


if __name__ == "__main__":
    gerar()
