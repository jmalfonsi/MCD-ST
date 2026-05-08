from __future__ import annotations

from datetime import UTC, datetime

from mcdst.utils import is_number, is_year, normalize, normalize_upper


def normalize_sex(value: str) -> str:
    n = normalize(value)
    if n in {"f", "femme"}:
        return "F"
    if n in {"m", "h", "homme"}:
        return "M"
    return "INCONNU" if value else ""


def classify_size(value: str) -> str:
    if not is_number(value):
        return ""
    number = int(float(value.replace(",", ".")))
    if number < 11:
        return "TPE_1_10"
    if number < 50:
        return "PME_11_49"
    if number < 250:
        return "ETI_50_249"
    return "GE_250_PLUS"


def apply_transform(transform: str | None, value: str) -> str:
    if transform == "normalize_sex":
        return normalize_sex(value)
    if transform == "normalize_visit_type":
        return normalize_visit_type(value)
    if transform == "normalize_conclusion":
        return normalize_conclusion(value)
    if transform == "normalize_exposure":
        return normalize_exposure(value)
    if transform == "exposure_category":
        return exposure_category(value)
    if transform == "to_flag":
        return to_flag(value)
    if transform == "classify_size":
        return classify_size(value)
    return value


def value_mapping_status(transform: str, source_value: str, target_value: str) -> str:
    if not source_value:
        return "ignore_empty"
    if transform == "normalize_visit_type" and target_value not in {"REPRISE", "PRE_REPRISE", "VIP_PERIODIQUE"}:
        return "a_revoir"
    if transform == "normalize_conclusion" and target_value not in {
        "APTE",
        "APTE_AVEC_RESTRICTION",
        "INAPTE",
        "ORIENTATION_PDP",
    }:
        return "a_revoir"
    known_exposures = {"POUSSIERES_BOIS", "MANUTENTION_MANUELLE", "GESTES_REPETITIFS"}
    if transform == "normalize_exposure" and target_value not in known_exposures:
        return "a_revoir"
    if transform == "exposure_category" and target_value == "AUTRE":
        return "a_revoir"
    if transform == "normalize_sex" and target_value == "INCONNU":
        return "a_revoir"
    if transform == "classify_size" and not target_value:
        return "a_revoir"
    return "auto"


def age_class(year: str) -> str:
    if not is_year(year):
        return ""
    age = datetime.now(UTC).year - int(year)
    if age < 30:
        return "AGE_18_29"
    if age < 45:
        return "AGE_30_44"
    if age < 55:
        return "AGE_45_54"
    return "AGE_55_PLUS"


def normalize_visit_type(value: str) -> str:
    n = normalize(value)
    if n in {"vr", "visitereprise"}:
        return "REPRISE"
    if "prereprise" in n or ("pre" in n and "reprise" in n):
        return "PRE_REPRISE"
    if "reprise" in n:
        return "REPRISE"
    if "period" in n or "vip" in n:
        return "VIP_PERIODIQUE"
    return normalize_upper(value)


def normalize_conclusion(value: str) -> str:
    n = normalize(value)
    if "pdp" in n:
        return "ORIENTATION_PDP"
    if "restriction" in n:
        return "APTE_AVEC_RESTRICTION"
    if "inapte" in n:
        return "INAPTE"
    if "apte" in n:
        return "APTE"
    return normalize_upper(value)


def to_flag(value: str) -> str:
    n = normalize(value)
    if not n or n in {"non", "false", "0", "aucun", "aucune"}:
        return "false"
    return "true"


def normalize_exposure(value: str) -> str:
    n = normalize(value)
    if "bois" in n or "chim" in n or "poussiere" in n:
        return "POUSSIERES_BOIS"
    if "manutention" in n:
        return "MANUTENTION_MANUELLE"
    if "repetitif" in n or "gestes" in n:
        return "GESTES_REPETITIFS"
    return normalize_upper(value)


def exposure_category(value: str) -> str:
    n = normalize(value)
    if "bois" in n or "chim" in n or "poussiere" in n:
        return "CHIMIQUE"
    if "manutention" in n or "repetitif" in n or "gestes" in n:
        return "BIOMECANIQUE"
    if "bruit" in n:
        return "BRUIT"
    return "AUTRE"
