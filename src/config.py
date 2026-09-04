# -*- coding: utf-8 -*-
"""Constantes compartilhadas pelo pipeline do projeto."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW_CENSO = RAIZ / "data" / "raw" / "censo2022"
DIR_RAW_CADUNICO = RAIZ / "data" / "raw" / "cadunico"
DIR_PROCESSED = RAIZ / "data" / "processed"

# Códigos oficiais do IBGE (API de localidades, distritos de Brumadinho/MG,
# confirmados em 04/09/2026 — ver docs/01_mapeamento_extracao.md)
CD_MUNICIPIO_BRUMADINHO = "3109006"

# Código de distrito com 9 dígitos (7 do município + 2 do distrito)
DISTRITOS_ALVO = {
    "310900615": "Conceição de Itaguá",
    "310900625": "São José do Paraopeba",
}

# Sufixo de 2 dígitos, para arquivos que trazem o distrito separado do município
SUFIXO_DISTRITO_ALVO = {
    "15": "Conceição de Itaguá",
    "25": "São José do Paraopeba",
}

# Todos os distritos de Brumadinho, para referência/contexto
TODOS_DISTRITOS_BRUMADINHO = {
    "310900605": "Brumadinho (Sede)",
    "310900610": "Aranha",
    "310900615": "Conceição de Itaguá",
    "310900620": "Piedade do Paraopeba",
    "310900625": "São José do Paraopeba",
}
