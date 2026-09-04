"""Paleta e helpers de layout compartilhados pelos scripts de graficos."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

COR_TEXTO_PRIMARIO = "#0b0b0b"
COR_TEXTO_SECUNDARIO = "#52514e"
COR_TEXTO_MUTED = "#898781"
COR_GRADE = "#e1e0d9"
COR_SUPERFICIE = "#fcfcfb"

CATEGORICA = {
    1: "#2a78d6",
    2: "#eb6834",
    3: "#1baf7a",
    4: "#eda100",
    5: "#e87ba4",
    6: "#008300",
    7: "#4a3aa7",
    8: "#e34948",
}

# Cor fixa por distrito, para a identidade nao mudar entre graficos
COR_DISTRITO = {
    "Conceição de Itaguá": CATEGORICA[1],
    "São José do Paraopeba": CATEGORICA[2],
}
COR_MASCULINO = CATEGORICA[1]
COR_FEMININO = CATEGORICA[2]
COR_NEUTRA = "#c3c2b7"

FONTE_CENSO = "Fonte: Censo Demográfico 2022 / IBGE — Agregados por Distrito (ftp.ibge.gov.br)"


def aplicar_estilo() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "axes.edgecolor": COR_GRADE,
            "axes.labelcolor": COR_TEXTO_SECUNDARIO,
            "text.color": COR_TEXTO_PRIMARIO,
            "xtick.color": COR_TEXTO_MUTED,
            "ytick.color": COR_TEXTO_MUTED,
            "figure.facecolor": COR_SUPERFICIE,
            "axes.facecolor": COR_SUPERFICIE,
            "savefig.facecolor": COR_SUPERFICIE,
        }
    )


def rodape(fig, texto: str = FONTE_CENSO, nota: str | None = None) -> None:
    linha = texto if nota is None else f"{texto}\n{nota}"
    fig.text(0.01, 0.01, linha, fontsize=7.5, color=COR_TEXTO_MUTED, ha="left", va="bottom")


def titulo(fig, texto: str, subtitulo: str | None = None) -> float:
    """Titulo/subtitulo posicionados em polegadas a partir do topo, nao em
    fracao da figura. Retorna a fracao de altura livre, para usar como `top`."""
    fig_h = fig.get_size_inches()[1]
    fig.suptitle(
        texto, fontsize=14, fontweight="bold", color=COR_TEXTO_PRIMARIO,
        x=0.01, ha="left", y=1 - (0.05 / fig_h), va="top",
    )
    if subtitulo:
        fig.text(0.01, 1 - (0.42 / fig_h), subtitulo, fontsize=10,
                 color=COR_TEXTO_SECUNDARIO, ha="left", va="top")
        return 1 - (0.78 / fig_h)
    return 1 - (0.40 / fig_h)


def salvar(fig, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {destino}")
