"""
Gera um conjunto de PNGs para cada distrito separadamente, em
reports/figuras/<distrito>/.

Os graficos do 04_graficos_analise.py sempre comparam os dois distritos no
mesmo eixo. Aqui cada figura mostra um distrito so, para uso em relatorio ou
apresentacao sobre aquele distrito.

Le o JSON consolidado pelo 08_dados_site.py, entao depende dele.

Gera:
    reports/figuras/sao-jose-do-paraopeba/*.png
    reports/figuras/conceicao-de-itagua/*.png
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAIZ
from estilo_graficos import (
    CATEGORICA, COR_DISTRITO, COR_FEMININO, COR_GRADE, COR_MASCULINO, COR_NEUTRA,
    COR_SUPERFICIE, COR_TEXTO_MUTED, COR_TEXTO_PRIMARIO, COR_TEXTO_SECUNDARIO,
    FONTE_CENSO, aplicar_estilo, rodape, salvar, titulo,
)

aplicar_estilo()

DIR_FIGURAS = RAIZ / "reports" / "figuras"
CAMINHO_DADOS = RAIZ / "site" / "dados" / "indicadores.json"


def _slug(nome: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", nome) if not unicodedata.combining(c)
    )
    return sem_acento.lower().replace(" ", "-")


def _barras_horizontais(pasta, nome_arquivo, itens, cor, titulo_texto, subtitulo, nota, formato="{:.1f}%", campo="pct"):
    itens = [i for i in itens if i.get(campo) is not None]
    fig, eixo = plt.subplots(figsize=(9, 0.44 * len(itens) + 2.0))
    y = np.arange(len(itens))[::-1]
    valores = [i[campo] for i in itens]
    barras = eixo.barh(y, valores, color=cor if isinstance(cor, str) else [cor(i) for i in itens], height=0.62)
    eixo.set_yticks(y)
    eixo.set_yticklabels([i["rotulo"] for i in itens], fontsize=9.5)
    eixo.set_xlim(0, max(valores) * 1.22 if valores else 1)
    eixo.spines[["top", "right", "bottom"]].set_visible(False)
    eixo.set_xticks([])
    for barra, v in zip(barras, valores):
        eixo.text(barra.get_width() + max(valores) * 0.015, barra.get_y() + barra.get_height() / 2,
                  formato.format(v), va="center", fontsize=9, fontweight="bold", color=COR_TEXTO_PRIMARIO)
    topo = titulo(fig, titulo_texto, subtitulo)
    rodape(fig, nota=nota)
    fig.tight_layout(rect=[0, 0.1, 1, topo])
    salvar(fig, pasta / nome_arquivo)


def _piramide(pasta, distrito, dados):
    faixas = [d["faixa"] for d in dados]
    total = sum(d["homens"] + d["mulheres"] for d in dados) or 1
    ph = [-100 * d["homens"] / total for d in dados]
    pm = [100 * d["mulheres"] / total for d in dados]

    fig, eixo = plt.subplots(figsize=(9, 5))
    y = np.arange(len(faixas))
    eixo.barh(y, ph, color=COR_MASCULINO, label="Homens", height=0.72)
    eixo.barh(y, pm, color=COR_FEMININO, label="Mulheres", height=0.72)
    for yi, v in zip(y, ph):
        eixo.text(v - 0.15, yi, f"{-v:.1f}%", ha="right", va="center", fontsize=8, color=COR_TEXTO_SECUNDARIO)
    for yi, v in zip(y, pm):
        eixo.text(v + 0.15, yi, f"{v:.1f}%", ha="left", va="center", fontsize=8, color=COR_TEXTO_SECUNDARIO)
    eixo.set_yticks(y)
    eixo.set_yticklabels(faixas, fontsize=9)
    limite = max(max(abs(v) for v in ph), max(pm)) * 1.35
    eixo.set_xlim(-limite, limite)
    eixo.axvline(0, color=COR_GRADE, linewidth=1)
    eixo.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{abs(x):.0f}%"))
    eixo.spines[["top", "right"]].set_visible(False)
    eixo.legend(loc="lower right", fontsize=9, frameon=False)

    topo = titulo(fig, f"Pirâmide etária — {distrito}",
                  f"% da população residente ({total:,.0f} pessoas)".replace(",", "."))
    rodape(fig, nota="Variáveis V01009–V01030, arquivo 'demografia'.")
    fig.tight_layout(rect=[0, 0.09, 1, topo])
    salvar(fig, pasta / "02_piramide_etaria.png")


def _empilhada(pasta, nome_arquivo, partes, titulo_texto, subtitulo, nota):
    fig, eixo = plt.subplots(figsize=(10, 2.9))
    cores = [CATEGORICA[i] for i in [1, 3, 4, 2, 8, 7, 5, 6]]
    esquerda = 0.0
    for idx, parte in enumerate(partes):
        eixo.barh([0], [parte["pct"]], left=[esquerda], height=0.42,
                  color=cores[idx % len(cores)], label=parte["rotulo"])
        if parte["pct"] >= 6:
            eixo.text(esquerda + parte["pct"] / 2, 0, f"{parte['pct']:.0f}%", ha="center", va="center",
                      fontsize=9, fontweight="bold", color="white")
        esquerda += parte["pct"]
    eixo.set_xlim(0, 100)
    eixo.set_yticks([])
    eixo.set_xlabel("% dos domicílios particulares permanentes ocupados", fontsize=9, color=COR_TEXTO_SECUNDARIO)
    eixo.spines[["top", "right", "left"]].set_visible(False)
    eixo.legend(loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=3, fontsize=8, frameon=False)
    topo = titulo(fig, titulo_texto, subtitulo)
    rodape(fig, nota=nota)
    fig.tight_layout(rect=[0, 0.22, 1, topo])
    salvar(fig, pasta / nome_arquivo)


def _colunas(pasta, nome_arquivo, rotulos, valores, cor, titulo_texto, subtitulo, nota, sufixo=""):
    fig, eixo = plt.subplots(figsize=(10, 4.2))
    x = np.arange(len(rotulos))
    cores = cor if isinstance(cor, str) else [cor(r) for r in rotulos]
    barras = eixo.bar(x, valores, color=cores, width=0.62)
    for barra, v in zip(barras, valores):
        eixo.text(barra.get_x() + barra.get_width() / 2, barra.get_height(),
                  f"{v:,.0f}{sufixo}".replace(",", "."), ha="center", va="bottom", fontsize=9,
                  fontweight="bold", color=COR_TEXTO_PRIMARIO)
    eixo.set_xticks(x)
    eixo.set_xticklabels(rotulos, fontsize=9, rotation=22, ha="right")
    eixo.spines[["top", "right"]].set_visible(False)
    eixo.yaxis.grid(True, color=COR_GRADE, linewidth=0.8)
    eixo.set_axisbelow(True)
    eixo.margins(y=0.18)
    topo = titulo(fig, titulo_texto, subtitulo)
    rodape(fig, nota=nota)
    fig.tight_layout(rect=[0, 0.1, 1, topo])
    salvar(fig, pasta / nome_arquivo)


def _resumo(pasta, distrito, d):
    r = d["resumo"]
    metricas = [
        (f"{r['populacao']:,.0f}".replace(",", "."), "Pessoas residentes"),
        (f"{r['domicilios_ocupados']:,.0f}".replace(",", "."), "Domicílios ocupados"),
        (f"{r['area_km2']:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."), "Área (km²)"),
        (f"{r['densidade']:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."), "Hab. por km²"),
        (f"{d['escolas']['ativas']:.0f}", "Escolas em atividade"),
        (f"{d['saude_equipes']['equipes_que_atendem']:.0f}", "Equipes de saúde"),
    ]
    fig, eixos = plt.subplots(1, len(metricas), figsize=(13, 2.6))
    cor = COR_DISTRITO[distrito]
    for eixo, (valor, rotulo) in zip(eixos, metricas):
        eixo.axis("off")
        eixo.add_patch(plt.Rectangle((0, 0.97), 1, 0.06, transform=eixo.transAxes, color=cor, clip_on=False, linewidth=0))
        eixo.text(0, 0.78, valor, transform=eixo.transAxes, fontsize=20, fontweight="bold",
                  color=COR_TEXTO_PRIMARIO, ha="left", va="top")
        eixo.text(0, 0.40, rotulo, transform=eixo.transAxes, fontsize=10,
                  color=COR_TEXTO_SECUNDARIO, ha="left", va="top")
    topo = titulo(fig, distrito, "Distrito de Brumadinho-MG — Censo 2022, Censo Escolar 2025 e CNES")
    rodape(fig, nota="Arquivo 'basico' do Censo 2022, Censo Escolar 2025 (INEP) e base de dados do CNES.")
    fig.subplots_adjust(left=0.02, right=0.98, wspace=0.35, bottom=0.16, top=topo)
    salvar(fig, pasta / "01_resumo.png")


def gerar() -> None:
    if not CAMINHO_DADOS.exists():
        raise FileNotFoundError(f"{CAMINHO_DADOS} nao existe. Rode antes: python src/08_dados_site.py")
    dados = json.loads(CAMINHO_DADOS.read_text(encoding="utf-8"))

    for distrito in dados["distritos"]:
        d = dados["por_distrito"][distrito]
        cor = COR_DISTRITO[distrito]
        pasta = DIR_FIGURAS / _slug(distrito)
        print(f"\n{distrito} -> {pasta.relative_to(RAIZ)}")

        _resumo(pasta, distrito, d)
        _piramide(pasta, distrito, d["piramide"])

        _barras_horizontais(pasta, "03_cor_ou_raca.png", d["cor_raca"], lambda i: CATEGORICA[1],
                            f"População por cor ou raça — {distrito}", "% da população residente",
                            "Variáveis V01317–V01321, arquivo 'cor_ou_raca'.")

        _barras_horizontais(pasta, "04_cor_raca_responsavel.png", d["cor_raca_responsavel"], lambda i: CATEGORICA[7],
                            f"Cor ou raça de quem responde pelo domicílio — {distrito}",
                            "% dos domicílios particulares permanentes ocupados",
                            "Soma das variáveis V01254–V01263, arquivo 'obitos'.")

        alfab = d["alfabetizacao"]["por_idade"]
        _colunas(pasta, "05_alfabetizacao_por_idade.png",
                 [f["faixa"] for f in alfab], [f["taxa"] or 0 for f in alfab], cor,
                 f"Taxa de alfabetização por faixa etária — {distrito}",
                 "Mostra em quais gerações a iliteracia está concentrada",
                 "Alfabetizados (V00748–V00760) sobre o total (V00644–V00656) de cada faixa.", sufixo="%")

        san = d["saneamento"]
        _empilhada(pasta, "06_abastecimento_agua.png", san["agua"], f"Abastecimento de água — {distrito}",
                   "Proxy de saneamento básico, não indicador de saúde",
                   "Variáveis V00111–V00118, arquivo 'caracteristicas_domicilio2'.")
        _empilhada(pasta, "07_esgotamento_sanitario.png", san["esgoto"], f"Esgotamento sanitário — {distrito}",
                   "Proxy de saneamento básico, não indicador de saúde",
                   "Variáveis V00309–V00316, arquivo 'caracteristicas_domicilio2'.")
        _empilhada(pasta, "08_destino_lixo.png", san["lixo"], f"Destino do lixo — {distrito}",
                   "Proxy de condições ambientais e sanitárias",
                   "Variáveis V00397–V00402, arquivo 'caracteristicas_domicilio2'.")

        _barras_horizontais(pasta, "09_composicao_domiciliar.png", d["domicilios"]["composicao"], cor,
                            f"Composição das unidades domésticas — {distrito}",
                            "% dos domicílios, por tipo de arranjo familiar",
                            "Variáveis V01209–V01212, arquivo 'parentesco'.")

        ob = d["obitos"]
        _colunas(pasta, "10_obitos_por_semestre.png",
                 [p["periodo"] for p in ob["por_periodo"]], [p["valor"] for p in ob["por_periodo"]],
                 lambda r: CATEGORICA[8] if r in ("1º sem. 2019", "1º sem. 2021") else cor,
                 f"Óbitos declarados por semestre — {distrito}",
                 "Rompimento da barragem em 25/01/2019 e segunda onda da covid-19 no 1º semestre de 2021",
                 "Variáveis V01264–V01270, arquivo 'obitos'. O Censo registra o semestre, não a causa.")

        etapas = [e for e in d["escolas"]["por_etapa"] if e["valor"] > 0]
        if etapas:
            _colunas(pasta, "11_matriculas_por_etapa.png",
                     [e["rotulo"] for e in etapas], [e["valor"] for e in etapas], cor,
                     f"Matrículas por etapa de ensino — {distrito}",
                     f"{d['escolas']['matriculas']:,.0f} matrículas na educação básica".replace(",", "."),
                     "Censo Escolar 2025 (INEP). Etapas ausentes não são ofertadas em escolas do distrito.")

        serie = d["serie_2010"]
        fig, eixo = plt.subplots(figsize=(9, 4.2))
        x = np.arange(len(serie))
        largura = 0.36
        for i, (ano, cor_ano) in enumerate([("2010", COR_NEUTRA), ("2022", cor)]):
            valores = [t[ano] for t in serie]
            barras = eixo.bar(x + (i - 0.5) * largura, valores, width=largura, color=cor_ano, label=ano)
            for barra, v in zip(barras, valores):
                eixo.text(barra.get_x() + barra.get_width() / 2, barra.get_height(), f"{v:.1f}%",
                          ha="center", va="bottom", fontsize=8.5, color=COR_TEXTO_PRIMARIO)
        eixo.set_xticks(x)
        eixo.set_xticklabels([t["indicador"] for t in serie], fontsize=9)
        eixo.set_ylim(0, 108)
        eixo.spines[["top", "right"]].set_visible(False)
        eixo.yaxis.grid(True, color=COR_GRADE, linewidth=0.8)
        eixo.set_axisbelow(True)
        eixo.legend(fontsize=9, frameon=False)
        topo = titulo(fig, f"Saneamento em 2010 e 2022 — {distrito}",
                      "Só estes três indicadores têm definição equivalente nos dois censos")
        rodape(fig, nota="Censo 2010 (agregados por setor censitário) e Censo 2022 (agregados por distrito). "
                         "O número de domicílios cresceu entre os censos: queda de percentual pode ser rede que não acompanhou o crescimento.")
        fig.tight_layout(rect=[0, 0.12, 1, topo])
        salvar(fig, pasta / "12_saneamento_2010_2022.png")

        _barras_horizontais(pasta, "13_renda_2010.png", d["renda_2010"],
                            lambda i: CATEGORICA[8] if i["rotulo"] in ("Até 1/8 SM", "1/8 a 1/4 SM", "1/4 a 1/2 SM") else CATEGORICA[3],
                            f"Renda domiciliar per capita em 2010 — {distrito}",
                            "% dos domicílios particulares por faixa de rendimento",
                            "Censo 2010, arquivo DomicilioRenda. Em 2022 a renda só é publicada até município.")

        if d["quilombolas"]["total"] > 0:
            q = d["quilombolas"]
            _barras_horizontais(pasta, "14_quilombolas.png",
                                [{"rotulo": f["faixa"], "pct": 100 * f["valor"] / q["total"], "valor": f["valor"]}
                                 for f in q["por_idade"]],
                                lambda i: CATEGORICA[7],
                                f"População quilombola por faixa etária — {distrito}",
                                f"{q['total']:.0f} pessoas se declararam quilombolas",
                                "Variáveis V03199–V03203, arquivo 'pessoas_quilombolas'.")


if __name__ == "__main__":
    print("Gerando gráficos por distrito ...")
    gerar()
    print("\nConcluído.")
