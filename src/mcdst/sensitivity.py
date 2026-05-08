from __future__ import annotations

from mcdst.utils import normalize


def infer_sensitivity(name: str, filename: str) -> str:
    column_name = normalize(name)
    context = normalize(f"{filename} {name}")
    s4_tokens = [
        "nom",
        "prenom",
        "mail",
        "email",
        "telephone",
        "tel",
        "adresse",
        "nir",
        "ins",
        "siret",
        "siren",
        "raisonsociale",
        "commentairemedical",
        "commentaire",
        "adherent",
        "nomusuel",
        "courrier",
        "pdf",
        "note",
        "cr",
    ]
    if any(token in column_name for token in s4_tokens):
        return "S4"
    if any(token in column_name for token in ["idsal", "idtravailleur", "idsalarie", "matricule", "clepers"]):
        return "S2"
    if any(token in column_name for token in ["anneen", "civilitesexe", "libemploi", "utlib"]):
        return "S2"

    s3_tokens = [
        "visite",
        "avis",
        "conclusion",
        "restriction",
        "amenagement",
        "adaptation",
        "reserve",
        "decision",
        "nature",
        "raison",
        "inaptitude",
        "nuisance",
        "risque",
        "exposition",
        "motif",
        "pdp",
        "sante",
        "niveau",
        "classe",
        "origine",
    ]
    if any(token in context for token in s3_tokens):
        return "S3"

    s2_tokens = ["sal", "salarie", "travailleur", "poste", "service", "ut", "suivi", "sexe", "naiss"]
    if any(token in context for token in s2_tokens):
        return "S2"
    return "S1"
