"""
Gera os gráficos em reports/figuras/ a partir dos CSVs já tratados em
data/processed/.

Não há gráfico de renda nem de saúde por distrito: o Censo 2022 não abre esses
dados abaixo do nível municipal (ver docs/01_mapeamento_extracao.md). Os
gráficos de saneamento servem de proxy, o que cada um explicita no rodapé.

Uso:
    python src/04_graficos_analise.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DIR_PROCESSED, RAIZ
from estilo_graficos import (
    CATEGORICA, COR_DISTRITO, COR_FEMININO, COR_GRADE, COR_MASCULINO, COR_NEUTRA,
    COR_SUPERFICIE, COR_TEXTO_MUTED, COR_TEXTO_PRIMARIO, COR_TEXTO_SECUNDARIO,
    FONTE_CENSO, aplicar_estilo, rodape as _rodape, salvar, titulo as _titulo,
)

aplicar_estilo()

DIR_FIGURAS = RAIZ / "reports" / "figuras"





def _salvar(fig, nome_arquivo: str) -> None:
    salvar(fig, DIR_FIGURAS / nome_arquivo)


def _carregar(nome_tema: str) -> pd.DataFrame:
    caminho = DIR_PROCESSED / f"censo2022_{nome_tema}_distritos.csv"
    df = pd.read_csv(caminho)
    return df.set_index("distrito_alvo")


def _valor(df: pd.DataFrame, distrito: str, coluna: str) -> float:
    """Lê um valor como número. O IBGE grava alguns decimais com vírgula
    (AREA_KM2 = '118,8365656'), que o pandas carrega como texto."""
    bruto = df.loc[distrito, coluna]
    if isinstance(bruto, str):
        bruto = bruto.replace(".", "").replace(",", ".")
    return float(bruto)


def grafico_resumo() -> None:
    basico = _carregar("basico")
    distritos = list(basico.index)

    fig, eixos = plt.subplots(1, 4, figsize=(13, 3.2))
    metricas = [
        ("v0001", "População\n(pessoas)", "{:,.0f}"),
        ("v0002", "Domicílios totais", "{:,.0f}"),
        ("AREA_KM2", "Área (km²)", "{:,.1f}"),
    ]

    for eixo, (coluna, rotulo, fmt) in zip(eixos, metricas):
        valores = [_valor(basico, d, coluna) for d in distritos]
        cores = [COR_DISTRITO[d] for d in distritos]
        barras = eixo.bar(distritos, valores, color=cores, width=0.55)
        eixo.set_title(rotulo, fontsize=10, color=COR_TEXTO_SECUNDARIO)
        eixo.spines[["top", "right", "left"]].set_visible(False)
        eixo.set_yticks([])
        eixo.tick_params(axis="x", labelsize=8, rotation=15)
        for barra, v in zip(barras, valores):
            eixo.text(
                barra.get_x() + barra.get_width() / 2,
                barra.get_height(),
                fmt.format(v),
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
                color=COR_TEXTO_PRIMARIO,
            )
        eixo.margins(y=0.18)

    eixo = eixos[3]
    densidades = [
        _valor(basico, d, "v0001") / _valor(basico, d, "AREA_KM2") for d in distritos
    ]
    cores = [COR_DISTRITO[d] for d in distritos]
    barras = eixo.bar(distritos, densidades, color=cores, width=0.55)
    eixo.set_title("Densidade\n(hab/km²)", fontsize=10, color=COR_TEXTO_SECUNDARIO)
    eixo.spines[["top", "right", "left"]].set_visible(False)
    eixo.set_yticks([])
    eixo.tick_params(axis="x", labelsize=8, rotation=15)
    for barra, v in zip(barras, densidades):
        eixo.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height(),
            f"{v:,.1f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=COR_TEXTO_PRIMARIO,
        )
    eixo.margins(y=0.18)

    topo = _titulo(fig, "População, domicílios e área — 2022", "São José do Paraopeba e Conceição de Itaguá (distritos de Brumadinho-MG)")
    _rodape(
        fig,
        nota="Variáveis V0001 (Total de pessoas), V0002 (Total de domicílios) e AREA_KM2 — arquivo 'basico'.",
    )
    fig.tight_layout(rect=[0, 0.08, 1, topo])
    _salvar(fig, "01_populacao_domicilios_area.png")


def grafico_piramide() -> None:
    piramide = pd.read_csv(DIR_PROCESSED / "censo2022_piramide_etaria_distritos.csv")
    ordem_faixas = [
        "0 a 4 anos", "5 a 9 anos", "10 a 14 anos", "15 a 19 anos",
        "20 a 24 anos", "25 a 29 anos", "30 a 39 anos", "40 a 49 anos",
        "50 a 59 anos", "60 a 69 anos", "70 anos ou mais",
    ]

    fig, eixos = plt.subplots(1, 2, figsize=(12, 5.5), sharey=True)

    for eixo, distrito in zip(eixos, COR_DISTRITO.keys()):
        sub = piramide[piramide["distrito_alvo"] == distrito]
        total = sub[sub["sexo"] == "Total"]["populacao"].sum()

        homens = sub[sub["sexo"] == "Masculino"].set_index("faixa_etaria")["populacao"]
        mulheres = sub[sub["sexo"] == "Feminino"].set_index("faixa_etaria")["populacao"]
        homens = homens.reindex(ordem_faixas).fillna(0)
        mulheres = mulheres.reindex(ordem_faixas).fillna(0)

        pct_h = -100 * homens / total
        pct_m = 100 * mulheres / total

        y = np.arange(len(ordem_faixas))
        eixo.barh(y, pct_h, color=COR_MASCULINO, label="Homens", height=0.72)
        eixo.barh(y, pct_m, color=COR_FEMININO, label="Mulheres", height=0.72)

        for yi, v in zip(y, pct_h):
            eixo.text(v - 0.15, yi, f"{-v:.1f}%", ha="right", va="center", fontsize=7.5, color=COR_TEXTO_SECUNDARIO)
        for yi, v in zip(y, pct_m):
            eixo.text(v + 0.15, yi, f"{v:.1f}%", ha="left", va="center", fontsize=7.5, color=COR_TEXTO_SECUNDARIO)

        eixo.set_yticks(y)
        eixo.set_yticklabels(ordem_faixas, fontsize=9)
        maxv = max(pct_h.abs().max(), pct_m.abs().max()) * 1.35
        eixo.set_xlim(-maxv, maxv)
        eixo.axvline(0, color=COR_GRADE, linewidth=1)
        eixo.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{abs(x):.0f}%"))
        eixo.spines[["top", "right"]].set_visible(False)
        eixo.set_title(f"{distrito}\n(n = {total:,.0f} pessoas)", fontsize=11, color=COR_TEXTO_PRIMARIO)
        eixo.legend(loc="lower right", fontsize=8, frameon=False)

    topo = _titulo(fig, "Pirâmide etária — Censo 2022", "% da população residente por sexo e faixa de idade")
    _rodape(
        fig,
        nota="Variáveis V01009–V01030 (população por sexo e faixa etária) — arquivo 'demografia'. "
        "Pequenas diferenças residuais entre Homens+Mulheres e o Total (poucas unidades) vêm da "
        "proteção de confidencialidade do IBGE em setores pequenos (recodificação/supressão de células com 1–2 pessoas).",
    )
    fig.tight_layout(rect=[0, 0.09, 1, topo])
    _salvar(fig, "02_piramide_etaria.png")


def grafico_cor_raca() -> None:
    df = _carregar("cor_ou_raca")
    colunas = {
        "V01317": "Branca",
        "V01318": "Preta",
        "V01319": "Amarela",
        "V01320": "Parda",
        "V01321": "Indígena",
    }
    basico = _carregar("basico")

    fig, eixos = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for eixo, distrito in zip(eixos, COR_DISTRITO.keys()):
        total = _valor(basico, distrito, "v0001")
        valores = [df.loc[distrito, c] / total * 100 for c in colunas]
        barras = eixo.bar(list(colunas.values()), valores, color=CATEGORICA[1], width=0.6)
        for barra, v in zip(barras, valores):
            eixo.text(
                barra.get_x() + barra.get_width() / 2, barra.get_height(),
                f"{v:.1f}%", ha="center", va="bottom", fontsize=9, color=COR_TEXTO_PRIMARIO,
            )
        eixo.set_title(distrito, fontsize=11, color=COR_TEXTO_PRIMARIO)
        eixo.spines[["top", "right", "left"]].set_visible(False)
        eixo.set_yticks([])
        eixo.tick_params(axis="x", labelsize=9)
        eixo.margins(y=0.15)

    topo = _titulo(fig, "População por cor ou raça — 2022", "% da população residente")
    _rodape(fig, nota="Variáveis V01317–V01321 — arquivo 'cor_ou_raca'.")
    fig.tight_layout(rect=[0, 0.08, 1, topo])
    _salvar(fig, "03_cor_ou_raca.png")


def grafico_alfabetizacao() -> None:
    df = _carregar("alfabetizacao")

    fig, eixos = plt.subplots(1, 2, figsize=(9, 4.6))
    for eixo, distrito in zip(eixos, COR_DISTRITO.keys()):
        alfabetizados = _valor(df, distrito, "V00900")
        nao_alfabetizados = _valor(df, distrito, "V00901")
        total = alfabetizados + nao_alfabetizados
        valores = [alfabetizados, nao_alfabetizados]
        rotulos = [
            f"Alfabetizados\n{alfabetizados:,.0f} ({alfabetizados/total*100:.1f}%)",
            f"Não alfabetizados\n{nao_alfabetizados:,.0f} ({nao_alfabetizados/total*100:.1f}%)",
        ]
        eixo.pie(
            valores,
            colors=[CATEGORICA[1], COR_NEUTRA],
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.42, "edgecolor": COR_SUPERFICIE, "linewidth": 2},
            labels=rotulos,
            labeldistance=1.12,
            textprops={"fontsize": 8.5, "color": COR_TEXTO_SECUNDARIO},
        )
        eixo.set_title(distrito, fontsize=11, color=COR_TEXTO_PRIMARIO, pad=14)

    topo = _titulo(fig, "Alfabetização — pessoas de 15 anos ou mais (2022)")
    _rodape(fig, nota="Variáveis V00900 (sabe ler e escrever) e V00901 (não sabe) — arquivo 'alfabetizacao'.")
    fig.tight_layout(rect=[0, 0.07, 1, topo])
    _salvar(fig, "04_alfabetizacao.png")


def grafico_alfabetizacao_por_idade() -> None:
    """Taxa de alfabetização por faixa etária: mostra em quais gerações a
    iliteracia está concentrada."""
    df = _carregar("alfabetizacao")
    faixas_totais = {
        "V00644": "15-19", "V00645": "20-24", "V00646": "25-29", "V00647": "30-34",
        "V00648": "35-39", "V00649": "40-44", "V00650": "45-49", "V00651": "50-54",
        "V00652": "55-59", "V00653": "60-64", "V00654": "65-69", "V00655": "70-79",
        "V00656": "80+",
    }
    faixas_alfabetizados = {
        "V00748": "15-19", "V00749": "20-24", "V00750": "25-29", "V00751": "30-34",
        "V00752": "35-39", "V00753": "40-44", "V00754": "45-49", "V00755": "50-54",
        "V00756": "55-59", "V00757": "60-64", "V00758": "65-69", "V00759": "70-79",
        "V00760": "80+",
    }
    ordem = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-79", "80+"]

    fig, eixo = plt.subplots(figsize=(11, 4.5))
    x = np.arange(len(ordem))
    largura = 0.38

    for i, distrito in enumerate(COR_DISTRITO.keys()):
        taxas = []
        for faixa in ordem:
            col_total = [k for k, v in faixas_totais.items() if v == faixa][0]
            col_alf = [k for k, v in faixas_alfabetizados.items() if v == faixa][0]
            total = _valor(df, distrito, col_total)
            alf = _valor(df, distrito, col_alf)
            taxas.append(100 * alf / total if total > 0 else np.nan)
        deslocamento = (i - 0.5) * largura
        eixo.bar(x + deslocamento, taxas, width=largura, color=COR_DISTRITO[distrito], label=distrito)

    eixo.set_xticks(x)
    eixo.set_xticklabels([f"{f} anos" for f in ordem], fontsize=8.5, rotation=30, ha="right")
    eixo.set_ylabel("Taxa de alfabetização (%)", fontsize=9, color=COR_TEXTO_SECUNDARIO)
    eixo.set_ylim(0, 105)
    eixo.spines[["top", "right"]].set_visible(False)
    eixo.legend(loc="lower left", fontsize=9, frameon=False)
    eixo.yaxis.grid(True, color=COR_GRADE, linewidth=0.8)
    eixo.set_axisbelow(True)

    topo = _titulo(fig, "Taxa de alfabetização por faixa etária — 2022", "Mostra em quais gerações a iliteracia está concentrada")
    _rodape(
        fig,
        nota="Alfabetizados (V00748–V00760) / Total (V00644–V00656) por faixa etária — arquivo 'alfabetizacao'.",
    )
    fig.tight_layout(rect=[0, 0.1, 1, topo])
    _salvar(fig, "04b_alfabetizacao_por_idade.png")


def _grafico_barra_empilhada_100(
    df: pd.DataFrame,
    colunas: dict[str, str],
    titulo: str,
    subtitulo: str,
    nome_arquivo: str,
    nota_fonte: str,
) -> None:
    """Barra 100% empilhada horizontal, uma linha por distrito. Altura e
    posição da legenda são calculadas em polegadas a partir do número de
    categorias, para a legenda não invadir o rodapé quando esse número muda."""
    distritos = list(COR_DISTRITO.keys())
    n_col_legenda = 3
    n_linhas_legenda = -(-len(colunas) // n_col_legenda)

    altura_rodape = 0.40
    altura_legenda = 0.24 * n_linhas_legenda + 0.10
    altura_eixo_x = 0.45
    folga = 0.12
    altura_inferior = altura_rodape + altura_legenda + altura_eixo_x + folga
    altura_barras = 0.85 * len(distritos) + 0.5
    altura_titulo = 0.95 if subtitulo else 0.55
    fig_h = altura_inferior + altura_barras + altura_titulo

    fig, eixo = plt.subplots(figsize=(11, fig_h))
    y = np.arange(len(distritos))

    totais = {d: sum(df.loc[d, c] for c in colunas) for d in distritos}
    esquerda = {d: 0.0 for d in distritos}

    cores_categoria = [CATEGORICA[i] for i in [1, 3, 4, 2, 8, 7, 5, 6]]

    for idx, (coluna, rotulo) in enumerate(colunas.items()):
        cor = cores_categoria[idx % len(cores_categoria)]
        valores = [100 * df.loc[d, coluna] / totais[d] for d in distritos]
        eixo.barh(y, valores, left=[esquerda[d] for d in distritos], color=cor, height=0.55, label=rotulo)
        for yi, v, esq in zip(y, valores, [esquerda[d] for d in distritos]):
            if v >= 5:
                eixo.text(esq + v / 2, yi, f"{v:.0f}%", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
        for d, v in zip(distritos, valores):
            esquerda[d] += v

    eixo.set_yticks(y)
    eixo.set_yticklabels(distritos, fontsize=10)
    eixo.set_xlim(0, 100)
    eixo.set_xlabel("% dos domicílios particulares permanentes ocupados", fontsize=9, color=COR_TEXTO_SECUNDARIO)
    eixo.spines[["top", "right", "left"]].set_visible(False)

    handles, labels = eixo.get_legend_handles_labels()
    y_legenda = (altura_rodape + altura_legenda / 2) / fig_h
    fig.legend(
        handles, labels, loc="center", bbox_to_anchor=(0.5, y_legenda),
        ncol=n_col_legenda, fontsize=8, frameon=False,
    )

    topo = _titulo(fig, titulo, subtitulo)
    _rodape(fig, nota=nota_fonte)
    fig.subplots_adjust(left=0.155, right=0.98, bottom=altura_inferior / fig_h, top=topo)
    _salvar(fig, nome_arquivo)


def grafico_agua() -> None:
    df = _carregar("caracteristicas_domicilio2")
    colunas = {
        "V00111": "Rede geral",
        "V00112": "Poço profundo/artesiano",
        "V00113": "Poço raso/cacimba",
        "V00114": "Fonte/nascente",
        "V00115": "Carro-pipa",
        "V00116": "Água da chuva armazenada",
        "V00117": "Rios/açudes/córregos/lagos",
        "V00118": "Outra forma",
    }
    _grafico_barra_empilhada_100(
        df, colunas,
        "Abastecimento de água — 2022",
        "Proxy de acesso a saneamento básico (não é indicador de saúde direto)",
        "05_abastecimento_agua.png",
        "Variáveis V00111–V00118 — arquivo 'caracteristicas_domicilio2'.",
    )


def grafico_esgoto() -> None:
    df = _carregar("caracteristicas_domicilio2")
    colunas = {
        "V00309": "Rede geral/pluvial",
        "V00310": "Fossa séptica ligada à rede",
        "V00311": "Fossa séptica não ligada à rede",
        "V00312": "Fossa rudimentar/buraco",
        "V00313": "Vala",
        "V00314": "Rio/lago/córrego/mar",
        "V00315": "Outra forma",
        "V00316": "Sem banheiro/sanitário",
    }
    _grafico_barra_empilhada_100(
        df, colunas,
        "Esgotamento sanitário — 2022",
        "Proxy de acesso a saneamento básico (não é indicador de saúde direto)",
        "06_esgotamento_sanitario.png",
        "Variáveis V00309–V00316 — arquivo 'caracteristicas_domicilio2'.",
    )


def grafico_lixo() -> None:
    df = _carregar("caracteristicas_domicilio2")
    colunas = {
        "V00397": "Coletado por serviço de limpeza",
        "V00398": "Depositado em caçamba",
        "V00399": "Queimado na propriedade",
        "V00400": "Enterrado na propriedade",
        "V00401": "Jogado em terreno baldio/encosta",
        "V00402": "Outro destino",
    }
    _grafico_barra_empilhada_100(
        df, colunas,
        "Destino do lixo — 2022",
        "Proxy de condições ambientais/sanitárias (não é indicador de saúde direto)",
        "07_destino_lixo.png",
        "Variáveis V00397–V00402 — arquivo 'caracteristicas_domicilio2'.",
    )


def grafico_banheiro() -> None:
    df = _carregar("caracteristicas_domicilio2")
    fig, eixos = plt.subplots(1, 2, figsize=(9, 4.6))
    for eixo, distrito in zip(eixos, COR_DISTRITO.keys()):
        com = _valor(df, distrito, "V00494")
        sem = _valor(df, distrito, "V00495")
        total = com + sem
        eixo.pie(
            [com, sem],
            colors=[CATEGORICA[1], COR_NEUTRA],
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.42, "edgecolor": COR_SUPERFICIE, "linewidth": 2},
            labels=[
                f"Com banheiro exclusivo\n{com:,.0f} ({com/total*100:.1f}%)",
                f"Sem banheiro exclusivo\n{sem:,.0f} ({sem/total*100:.1f}%)",
            ],
            labeldistance=1.12,
            textprops={"fontsize": 8.5, "color": COR_TEXTO_SECUNDARIO},
        )
        eixo.set_title(distrito, fontsize=11, color=COR_TEXTO_PRIMARIO, pad=14)

    topo = _titulo(fig, "Banheiro de uso exclusivo com chuveiro e vaso sanitário — 2022")
    _rodape(fig, nota="Variáveis V00494/V00495 — arquivo 'caracteristicas_domicilio2'.")
    fig.tight_layout(rect=[0, 0.07, 1, topo])
    _salvar(fig, "08_banheiro_exclusivo.png")


def grafico_composicao_domiciliar() -> None:
    df = _carregar("parentesco")
    colunas = {
        "V01209": "Unipessoal (mora sozinho)",
        "V01210": "Nuclear",
        "V01211": "Estendida",
        "V01212": "Composta",
    }
    fig, eixo = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(colunas))
    largura = 0.38
    for i, distrito in enumerate(COR_DISTRITO.keys()):
        total = sum(df.loc[distrito, c] for c in colunas)
        valores = [100 * df.loc[distrito, c] / total for c in colunas]
        deslocamento = (i - 0.5) * largura
        barras = eixo.bar(x + deslocamento, valores, width=largura, color=COR_DISTRITO[distrito], label=distrito)
        for barra, v in zip(barras, valores):
            eixo.text(barra.get_x() + barra.get_width() / 2, barra.get_height(), f"{v:.0f}%", ha="center", va="bottom", fontsize=8)

    eixo.set_xticks(x)
    eixo.set_xticklabels(list(colunas.values()), fontsize=9)
    eixo.set_ylabel("% dos domicílios", fontsize=9, color=COR_TEXTO_SECUNDARIO)
    eixo.spines[["top", "right"]].set_visible(False)
    eixo.legend(loc="upper right", fontsize=9, frameon=False)
    eixo.yaxis.grid(True, color=COR_GRADE, linewidth=0.8)
    eixo.set_axisbelow(True)

    topo = _titulo(fig, "Composição das unidades domésticas — 2022", "% de domicílios por tipo de arranjo familiar — relevante para vulnerabilidade social (ex.: idosos morando sozinhos)")
    _rodape(fig, nota="Variáveis V01209–V01212 — arquivo 'parentesco'.")
    fig.tight_layout(rect=[0, 0.08, 1, topo])
    _salvar(fig, "09_composicao_domiciliar.png")


def grafico_contexto_municipal() -> None:
    """Indicadores do município inteiro, não dos distritos. Valores copiados
    à mão do painel IBGE Cidades (não há API tabular para esse painel); para
    atualizar, revisite a página e ajuste a lista abaixo.

    Formato de cartão em vez de barra porque PIB per capita, percentuais e
    IDHM têm unidades incompatíveis para dividir um eixo."""
    indicadores = [
        ("PIB per capita", "R$ 73.117", "IBGE/Atlas Brasil, 2023"),
        ("Pop. com renda per capita\naté 1/2 sal. mínimo", "33,5%", "IBGE, Censo 2010"),
        ("Mortalidade infantil", "18,1 ‰", "óbitos / mil nasc. vivos — IBGE, 2025"),
        ("Esgotamento sanitário\nadequado", "53,3%", "IBGE, indicadores municipais, 2022"),
        ("IDHM", "0,747", "IBGE/Atlas Brasil, 2010"),
    ]

    fig, eixos = plt.subplots(1, len(indicadores), figsize=(13, 3.4))
    cor_destaque = CATEGORICA[7]

    for eixo, (rotulo, valor, fonte_indiv) in zip(eixos, indicadores):
        eixo.axis("off")
        eixo.add_patch(
            plt.Rectangle((0, 0.98), 1, 0.05, transform=eixo.transAxes, color=cor_destaque, clip_on=False, linewidth=0)
        )
        eixo.text(0, 0.82, valor, transform=eixo.transAxes, fontsize=22, fontweight="bold", color=COR_TEXTO_PRIMARIO, ha="left", va="top")
        eixo.text(0, 0.48, rotulo, transform=eixo.transAxes, fontsize=10.5, color=COR_TEXTO_SECUNDARIO, ha="left", va="top", linespacing=1.4)
        eixo.text(0, 0.08, fonte_indiv, transform=eixo.transAxes, fontsize=7.5, color=COR_TEXTO_MUTED, ha="left", va="top")

    topo = _titulo(
        fig,
        "Contexto municipal — Brumadinho (não é dado por distrito)",
        "Renda e saúde não têm abertura oficial por distrito no Censo 2022 — ver docs/01_mapeamento_extracao.md",
    )
    _rodape(
        fig,
        nota="Fonte: IBGE Cidades, painel Brumadinho (cidades.ibge.gov.br/brasil/mg/brumadinho/panorama), consultado em 04/09/2026 "
        "(fonte original de cada indicador identificada em cada cartão acima).",
    )
    fig.subplots_adjust(left=0.02, right=0.98, wspace=0.35, bottom=0.16, top=topo)
    _salvar(fig, "10_contexto_municipal.png")


if __name__ == "__main__":
    print("Gerando gráficos em reports/figuras/ ...")
    grafico_resumo()
    grafico_piramide()
    grafico_cor_raca()
    grafico_alfabetizacao()
    grafico_alfabetizacao_por_idade()
    grafico_agua()
    grafico_esgoto()
    grafico_lixo()
    grafico_banheiro()
    grafico_composicao_domiciliar()
    grafico_contexto_municipal()
    print("Concluído.")
