"""Street-name abbreviation, shared by the index and the map labels.

Compresses the common Spanish title/rank words found in Buenos Aires street
names (AVENIDA -> AV., GENERAL -> GRAL., ...) to save space. Words already
abbreviated in the source data are left untouched. Accents are ignored when
matching so CAPITÁN and CAPITAN both hit.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

import yaml

_ABBREV_PATH = Path(__file__).resolve().parent / "abbreviations.yaml"

# Fallback used only if abbreviations.yaml is missing; the YAML is the source
# of truth and is meant to be edited.
_DEFAULT_ABBREV = {
    "AVENIDA": "AV.", "GENERAL": "GRAL.", "PRESIDENTE": "PRES.", "DOCTOR": "DR.",
    "DOCTORA": "DRA.", "CORONEL": "CNEL.", "INTENDENTE": "INT.", "GOBERNADOR": "GOB.",
    "TENIENTE": "TTE.", "SARGENTO": "SGTO.", "COMANDANTE": "CMTE.", "CAPITAN": "CAP.",
    "BRIGADIER": "BRIG.", "ALMIRANTE": "ALTE.", "INGENIERO": "ING.", "ARQUITECTO": "ARQ.",
    "PROFESOR": "PROF.", "PROFESORA": "PROFA.", "MONSENOR": "MONS.", "PRESBITERO": "PBRO.",
    "NUESTRA": "NTRA.", "SENORA": "SRA.", "HERMANOS": "HNOS.", "HERMANO": "HNO.",
    "DIPUTADO": "DIP.", "SENADOR": "SEN.", "PERIODISTA": "PER.", "MARISCAL": "MCAL.",
    "VIRREY": "VRREY.", "PASAJE": "PJE.", "DIAGONAL": "DIAG.",
}


def _norm(word: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", word.upper())
        if unicodedata.category(c) != "Mn"
    )


def _load_abbrev() -> dict:
    raw = _DEFAULT_ABBREV
    if _ABBREV_PATH.exists():
        loaded = yaml.safe_load(_ABBREV_PATH.read_text(encoding="utf-8"))
        if loaded:
            raw = loaded
    return {_norm(k): str(v) for k, v in raw.items()}


ABBREV = _load_abbrev()


def abbreviate(name: str) -> str:
    parts = []
    for tok in str(name).split():
        had_comma = tok.endswith(",")
        core = tok[:-1] if had_comma else tok
        rep = ABBREV.get(_norm(core.rstrip(".")), core)
        parts.append(rep + ("," if had_comma else ""))
    return " ".join(parts)
