"""
Consolida os CSVs tratados num unico JSON que o site (site/) le com D3.

O site e estatico: nao ha backend, entao todo recorte e calculo de percentual
que dependeria de codigo servidor e feito aqui.

Depende de ter rodado antes os scripts 01 a 12.

Gera:
    site/dados/indicadores.json
    site/dados/distritos.geojson
    site/dados/setores.geojson
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED, DISTRITOS_ALVO, RAIZ

DIR_SITE_DADOS = RAIZ / "site" / "dados"
DISTRITOS = list(DISTRITOS_ALVO.values())
FORA_DA_MALHA = {"sem coordenada", "fora dos limites do municipio"}

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
    # Conferido no dicionario do IBGE: V01228 e "0 a 4 anos", nao "menos de 1 ano"
    faixas = ["0 a 4 anos", "5 a 9 anos", "10 a 14 anos", "15 a 19 anos", "20 a 24 anos",
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
    por_periodo = [{"periodo": r, "valor": _num(df, distrito, c)} for c, r in periodos.items()]
    total = _num(df, distrito, "V01226") + _num(df, distrito, "V01227")
    com_idade = sum(f["homens"] + f["mulheres"] for f in por_idade)
    com_periodo = sum(p["valor"] for p in por_periodo)
    return {
        "domicilios_com_obito": _num(df, distrito, "V01224"),
        "domicilios_sem_obito": _num(df, distrito, "V01225"),
        "homens": _num(df, distrito, "V01226"),
        "mulheres": _num(df, distrito, "V01227"),
        "total": total,
        "por_idade": por_idade,
        "por_periodo": por_periodo,
        # Boa parte dos registros nao traz idade nem data: em area pequena o IBGE
        # suprime ou recodifica celulas com poucas ocorrencias. Sem essa cobertura
        # explicita, os dois graficos parecem mostrar o total de obitos e nao mostram.
        "cobertura_idade": com_idade,
        "cobertura_periodo": com_periodo,
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


def escolas(distrito: str) -> dict:
    """Censo Escolar do INEP. Aqui nao houve cruzamento geografico: os
    microdados ja trazem o codigo do distrito."""
    df = pd.read_csv(DIR_PROCESSED / "inep_escolas_brumadinho.csv")
    sub = df[df["distrito"] == distrito]
    ativas = sub[sub["situacao"] == "Em atividade"]
    etapas = [
        ("Educação infantil", "QT_MAT_INF"),
        ("Fundamental — anos iniciais", "QT_MAT_FUND_AI"),
        ("Fundamental — anos finais", "QT_MAT_FUND_AF"),
        ("Ensino médio", "QT_MAT_MED"),
    ]
    infra = [
        ("Água da rede pública", "IN_AGUA_REDE_PUBLICA"),
        ("Esgoto em rede pública", "IN_ESGOTO_REDE_PUBLICA"),
        ("Coleta de lixo", "IN_LIXO_SERVICO_COLETA"),
        ("Internet", "IN_INTERNET"),
        ("Biblioteca", "IN_BIBLIOTECA"),
        ("Laboratório de informática", "IN_LABORATORIO_INFORMATICA"),
        ("Quadra de esportes", "IN_QUADRA_ESPORTES"),
        ("Alimentação", "IN_ALIMENTACAO"),
    ]
    return {
        "total": int(len(sub)),
        "ativas": int(len(ativas)),
        "matriculas": float(ativas["QT_MAT_BAS"].fillna(0).sum()),
        "por_etapa": [
            {"rotulo": rotulo, "valor": float(ativas[col].fillna(0).sum())} for rotulo, col in etapas
        ],
        "infraestrutura": [
            {"rotulo": rotulo,
             "escolas": int(ativas[col].fillna(0).sum()),
             "pct": 100 * float(ativas[col].fillna(0).sum()) / len(ativas) if len(ativas) else None}
            for rotulo, col in infra
        ],
        "lista": [
            {"nome": r["NO_ENTIDADE"], "dependencia": r["dependencia"], "localizacao": r["localizacao"],
             "area_diferenciada": r["area_diferenciada"], "situacao": r["situacao"],
             "matriculas": None if pd.isna(r["QT_MAT_BAS"]) else float(r["QT_MAT_BAS"])}
            for _, r in sub.iterrows()
        ],
    }


def saude_equipes(distrito: str) -> dict:
    """Equipes e profissionais do CNES. 'sediadas' conta pela localizacao do
    estabelecimento; 'atendem' inclui equipe sediada fora cuja area de
    referencia cadastrada e o distrito."""
    equipes = pd.read_csv(DIR_PROCESSED / "cnes_equipes_brumadinho.csv")
    profissionais = pd.read_csv(DIR_PROCESSED / "cnes_profissionais_brumadinho.csv")
    sediadas = equipes[equipes["distrito"] == distrito]
    atendem = equipes[equipes["distrito_atendido"] == distrito]
    prof = profissionais[profissionais["distrito"] == distrito]
    return {
        "equipes_sediadas": int(len(sediadas)),
        "equipes_que_atendem": int(len(atendem)),
        "profissionais": int(len(prof)),
        "por_tipo_equipe": atendem["tipo_equipe"].value_counts().to_dict(),
        "lista_equipes": [
            {"tipo": r["tipo_equipe"], "referencia": r["NO_REFERENCIA"],
             "estabelecimento": r["estabelecimento"], "sediada_em": r["distrito"],
             "populacoes": r["populacoes_assistidas"] if isinstance(r["populacoes_assistidas"], str) else ""}
            for _, r in atendem.iterrows()
        ],
        "por_ocupacao": prof["ocupacao"].value_counts().head(12).to_dict(),
    }


def serie_2010(distrito: str) -> list[dict]:
    """Saneamento em 2010 e 2022 com definicoes equivalentes nos dois censos.
    As categorias mudaram entre eles: so estes tres indicadores tem
    correspondencia direta."""
    df10 = pd.read_csv(DIR_PROCESSED / "censo2010_distritos.csv").set_index("distrito")
    dom2 = _carregar("caracteristicas_domicilio2")

    def pct2022(numerador: list[str], denominador: range) -> float:
        base = sum(_num(dom2, distrito, f"V{n:05d}") for n in denominador)
        return 100 * sum(_num(dom2, distrito, c) for c in numerador) / base if base else 0.0

    linha = df10.loc[distrito]
    return [
        {"indicador": "Água da rede geral", "2010": float(linha["pct_agua_rede_geral"]),
         "2022": pct2022(["V00111"], range(111, 119))},
        {"indicador": "Esgoto em rede geral ou pluvial", "2010": float(linha["pct_esgoto_rede_geral"]),
         "2022": pct2022(["V00309"], range(309, 317))},
        {"indicador": "Lixo coletado", "2010": float(linha["pct_lixo_coletado"]),
         "2022": pct2022(["V00397", "V00398"], range(397, 403))},
    ]


def renda_2010(distrito: str) -> list[dict]:
    """Renda so existe por distrito no Censo 2010: em 2022 o tema saiu do
    universo e foi para a amostra, publicada ate municipio."""
    df = pd.read_csv(DIR_PROCESSED / "censo2010_distritos.csv").set_index("distrito")
    rotulos = {
        "renda_ate_1_8_sm": "Até 1/8 SM", "renda_1_8_a_1_4_sm": "1/8 a 1/4 SM",
        "renda_1_4_a_1_2_sm": "1/4 a 1/2 SM", "renda_1_2_a_1_sm": "1/2 a 1 SM",
        "renda_1_a_2_sm": "1 a 2 SM", "renda_2_a_3_sm": "2 a 3 SM",
        "renda_3_a_5_sm": "3 a 5 SM", "renda_5_a_10_sm": "5 a 10 SM",
        "renda_mais_10_sm": "Mais de 10 SM", "renda_sem_rendimento": "Sem rendimento",
    }
    linha = df.loc[distrito]
    valores = [(rotulo, float(linha[coluna])) for coluna, rotulo in rotulos.items()]
    total = sum(v for _, v in valores) or 1
    return [{"rotulo": r, "valor": v, "pct": 100 * v / total} for r, v in valores]


def barragens() -> dict:
    """Cadastro Nacional de Barragens de Mineracao (ANM) cruzado com a malha do
    IBGE. A B1 da Mina Corrego do Feijao, que rompeu em 2019, nao esta no
    cadastro: o que aparece sao as estruturas remanescentes da mesma mina."""
    df = pd.read_csv(DIR_PROCESSED / "anm_barragens_brumadinho.csv")
    feijao = df[df["mina"].astype(str).str.contains("Feij", na=False)]
    return {
        "total": int(len(df)),
        "em_emergencia": int((df["nivel_emergencia"] != "Sem emergência").sum()),
        "por_distrito": {
            distrito: {
                "total": int(len(sub)),
                "em_emergencia": int((sub["nivel_emergencia"] != "Sem emergência").sum()),
                "montante": int((sub["metodo_construtivo"] == "Alteamento a montante").sum()),
                "lista": [
                    {"nome": r["nome"], "empreendedor": r["empreendedor"], "mina": r["mina"] if isinstance(r["mina"], str) else "",
                     "emergencia": r["nivel_emergencia"], "risco": r["risco"], "dano": r["dano_potencial"],
                     "situacao": r["situacao"], "metodo": r["metodo_construtivo"],
                     "altura": r["altura_m"] if isinstance(r["altura_m"], str) else None,
                     "jusante": str(r["populacao_jusante"]).split(" (")[0]}
                    for _, r in sub.iterrows()
                ],
            }
            for distrito, sub in df.groupby("distrito")
        },
        "pontos": [
            {"nome": r["nome"], "distrito": r["distrito"], "emergencia": r["nivel_emergencia"],
             "mina": r["mina"] if isinstance(r["mina"], str) else "", "situacao": r["situacao"],
             "feijao": bool(isinstance(r["mina"], str) and "Feij" in r["mina"]),
             "lat": r["lat"], "lon": r["lon"]}
            for _, r in df.dropna(subset=["lat"]).iterrows()
        ],
        "mina_feijao": {
            "lat": float(feijao["lat"].mean()), "lon": float(feijao["lon"].mean()),
            "estruturas": int(len(feijao)),
        },
    }


def peso_da_mineracao() -> dict:
    """Participacao de cada setor no emprego e na massa salarial de Brumadinho.

    A massa salarial nao vem pronta: e reconstruida multiplicando o salario
    medio de cada classe da CNAE pelo numero de vinculos daquela classe, no
    mesmo corte por sexo (o unico que cobre todos os vinculos)."""
    grupos = ["Homem - Total", "Mulher - Total"]
    chave = ["Classe CNAE (5 dígitos)", "Sexo e Raça/Cor"]

    salarios = pd.read_csv(DIR_PROCESSED / "dataviva_salario_cnae_brumadinho.csv")
    salarios = salarios[(salarios["Indicador"] == "Média do Salário Real")
                        & (salarios["Sexo e Raça/Cor"].isin(grupos))]
    empregos = pd.read_csv(DIR_PROCESSED / "dataviva_emprego_cnae_brumadinho.csv")
    empregos = empregos[empregos["Sexo e Raça/Cor"].isin(grupos)]

    juncao = (empregos[chave + ["Valor", "Seção CNAE (1 dígito)"]].rename(columns={"Valor": "vinculos"})
              .merge(salarios[chave + ["Valor"]].rename(columns={"Valor": "salario"}), on=chave, how="inner"))
    juncao["massa"] = juncao["vinculos"] * juncao["salario"]

    setores = juncao.groupby("Seção CNAE (1 dígito)").agg(
        vinculos=("vinculos", "sum"), massa=("massa", "sum")).reset_index()
    total_vinculos = setores["vinculos"].sum()
    total_massa = setores["massa"].sum()
    media_municipio = total_massa / total_vinculos if total_vinculos else 0

    lista = [
        {
            "secao": r["Seção CNAE (1 dígito)"],
            "nome": SECOES_CNAE.get(r["Seção CNAE (1 dígito)"], r["Seção CNAE (1 dígito)"]),
            "vinculos": float(r["vinculos"]),
            "pct_vinculos": 100 * r["vinculos"] / total_vinculos,
            "pct_massa": 100 * r["massa"] / total_massa,
            "salario_medio": r["massa"] / r["vinculos"] if r["vinculos"] else 0,
        }
        for _, r in setores.sort_values("massa", ascending=False).iterrows()
    ]
    extrativa = next((x for x in lista if x["secao"] == "B"), None)
    return {
        "setores": lista,
        "media_municipio": media_municipio,
        "extrativa": extrativa,
        "razao_extrativa": extrativa["salario_medio"] / media_municipio if extrativa and media_municipio else None,
        "cobertura_vinculos": float(total_vinculos),
    }


def _distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    raio, rad = 6371.0, math.pi / 180
    a = (math.sin((lat2 - lat1) * rad / 2) ** 2
         + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin((lon2 - lon1) * rad / 2) ** 2)
    return 2 * raio * math.asin(math.sqrt(a))


def rompimento() -> dict:
    """Junta o que os dados deste projeto conseguem dizer sobre o rompimento da
    barragem da Mina Corrego do Feijao, em 25/01/2019.

    Nenhuma fonte aqui registra causa de morte nem area atingida: o que da pra
    medir e distancia, exposicao (de onde vem a agua do domicilio), o que existe
    de barragem hoje e o que mudou no cadastro de saude depois de 2019."""
    barr = barragens()
    mina = barr["mina_feijao"]
    geojson = json.loads((DIR_PROCESSED / "distritos_brumadinho.geojson").read_text(encoding="utf-8"))

    def pontos_da_geometria(geometria):
        saida = []
        def caminhar(c):
            if isinstance(c[0], (int, float)):
                saida.append(c)
            else:
                for i in c:
                    caminhar(i)
        caminhar(geometria["coordinates"])
        return saida

    distancias = []
    for f in geojson["features"]:
        pontos = pontos_da_geometria(f["geometry"])
        distancias.append({
            "distrito": f["properties"]["nm_dist"],
            "km": min(_distancia_km(mina["lat"], mina["lon"], p[1], p[0]) for p in pontos),
            "alvo": bool(f["properties"]["alvo"]),
        })
    distancias.sort(key=lambda d: d["km"])

    dom2 = _carregar("caracteristicas_domicilio2")
    fontes = {"V00111": "Rede geral", "V00112": "Poço profundo/artesiano", "V00113": "Poço raso/cacimba",
              "V00114": "Fonte/nascente", "V00115": "Carro-pipa", "V00116": "Água da chuva",
              "V00117": "Rios/açudes/córregos/lagos", "V00118": "Outra forma"}
    agua = {}
    for d in DISTRITOS:
        partes = _series(dom2, d, fontes)
        fora = sum(p["pct"] for p in partes if p["rotulo"] != "Rede geral")
        agua[d] = {
            "partes": partes,
            "fora_da_rede_pct": fora,
            "superficial_pct": next(p["pct"] for p in partes if p["rotulo"] == "Rios/açudes/córregos/lagos"),
        }

    equipes = pd.read_csv(DIR_PROCESSED / "cnes_equipes_brumadinho.csv")
    equipes["ano"] = pd.to_datetime(equipes["DT_ATIVACAO"], format="%d/%m/%Y", errors="coerce").dt.year
    por_ano = equipes["ano"].value_counts().sort_index()
    saude_mental = equipes[equipes["tipo_equipe"].str.contains("SAUDE MENTAL", na=False)]

    peso = peso_da_mineracao()

    caminho_serie = DIR_PROCESSED / "dataviva_emprego_cnae_serie_brumadinho.csv"
    emprego = []
    if caminho_serie.exists():
        serie = pd.read_csv(caminho_serie)
        total_por_ano = serie.groupby("Ano")["vinculos"].sum()
        for ano, sub in serie.groupby("Ano"):
            extrativa = float(sub[sub["secao"] == "B"]["vinculos"].sum())
            emprego.append({
                "ano": int(ano),
                "extrativa": extrativa,
                "total": float(total_por_ano[ano]),
                "pct": 100 * extrativa / total_por_ano[ano] if total_por_ano[ano] else 0,
            })

    return {
        "data": "25 de janeiro de 2019",
        "distancias": distancias,
        "agua": agua,
        "barragens": barr,
        "equipes_por_ano": [{"ano": int(a), "valor": int(v)} for a, v in por_ano.items()],
        "saude_mental": [
            {"referencia": r["NO_REFERENCIA"], "ano": None if pd.isna(r["ano"]) else int(r["ano"]),
             "estabelecimento": r["estabelecimento"]}
            for _, r in saude_mental.iterrows()
        ],
        "emprego_extrativa": emprego,
        "peso_setorial": peso,
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
                "dentro": r["distrito"] not in FORA_DA_MALHA,
                "sus": bool(r["sus"]),
                "lat": r["latitude_estabelecimento_decimo_grau"],
                "lon": r["longitude_estabelecimento_decimo_grau"],
            }
            for _, r in pontos.iterrows()
        ],
    }


def contexto_municipal() -> dict:
    emprego = pd.read_csv(DIR_PROCESSED / "dataviva_emprego_cnae_brumadinho.csv")
    # As categorias se sobrepoem (cortes por cor/raca e por sexo do mesmo
    # universo): somar as duas familias contaria cada vinculo duas vezes.
    emprego = emprego[emprego["Sexo e Raça/Cor"].isin(["Homem - Total", "Mulher - Total"])]
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
                "saude_equipes": saude_equipes(d),
                "escolas": escolas(d),
                "serie_2010": serie_2010(d),
                "renda_2010": renda_2010(d),
            }
            for d in DISTRITOS
        },
        "saude_pontos": saude["pontos"],
        "saude_municipio": saude["por_distrito"],
        "municipio": contexto_municipal(),
        "rompimento": rompimento(),
    }

    DIR_SITE_DADOS.mkdir(parents=True, exist_ok=True)
    destino = DIR_SITE_DADOS / "indicadores.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    shutil.copy(DIR_PROCESSED / "distritos_brumadinho.geojson", DIR_SITE_DADOS / "distritos.geojson")
    shutil.copy(DIR_PROCESSED / "setores_distritos.geojson", DIR_SITE_DADOS / "setores.geojson")
    print(f"-> {destino} ({destino.stat().st_size/1024:.0f} KB)")
    print(f"-> {DIR_SITE_DADOS / 'distritos.geojson'}")
    print(f"-> {DIR_SITE_DADOS / 'setores.geojson'}")
    return dados


if __name__ == "__main__":
    gerar()
