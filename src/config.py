"""Constantes compartilhadas pelo pipeline."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW_CENSO = RAIZ / "data" / "raw" / "censo2022"
DIR_RAW_MALHA = RAIZ / "data" / "raw" / "malha"
DIR_RAW_INEP = RAIZ / "data" / "raw" / "inep"
DIR_RAW_SETORES = RAIZ / "data" / "raw" / "setores"
DIR_RAW_CENSO2010 = RAIZ / "data" / "raw" / "censo2010"
DIR_RAW_CNES = RAIZ / "data" / "raw" / "cnes"
DIR_RAW_ANM = RAIZ / "data" / "raw" / "anm"
DIR_PROCESSED = RAIZ / "data" / "processed"

CD_MUNICIPIO_BRUMADINHO = "3109006"

# Código de distrito do IBGE: 7 dígitos do município + 2 do distrito
DISTRITOS_ALVO = {
    "310900615": "Conceição de Itaguá",
    "310900625": "São José do Paraopeba",
}

SUFIXO_DISTRITO_ALVO = {
    "15": "Conceição de Itaguá",
    "25": "São José do Paraopeba",
}

TODOS_DISTRITOS_BRUMADINHO = {
    "310900605": "Brumadinho (Sede)",
    "310900610": "Aranha",
    "310900615": "Conceição de Itaguá",
    "310900620": "Piedade do Paraopeba",
    "310900625": "São José do Paraopeba",
}
