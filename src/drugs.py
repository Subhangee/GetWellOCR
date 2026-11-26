"""Small reference list of common active ingredients (German spelling).

Used for two things:
  1. Spelling suggestions in the review screen ("Glimeprid" -> "Glimepirid").
  2. The "used for" line on the patient plan (common use only; the doctor checks).

Extend the list freely. Keys must be the German INN spelling.
"""
from rapidfuzz import fuzz, process

# active ingredient -> common-use category (see PURPOSES in export.py)
DRUGS = {
    "Ramipril": "bp", "Lisinopril": "bp", "Enalapril": "bp", "Candesartan": "bp",
    "Valsartan": "bp", "Amlodipin": "bp",
    "Metoprolol": "heart", "Metoprololsuccinat": "heart", "Bisoprolol": "heart",
    "Torasemid": "water", "Furosemid": "water", "Hydrochlorothiazid": "water",
    "Spironolacton": "water",
    "ASS": "thin", "Clopidogrel": "thin", "Apixaban": "thin", "Rivaroxaban": "thin",
    "Edoxaban": "thin",
    "Atorvastatin": "chol", "Simvastatin": "chol", "Rosuvastatin": "chol",
    "Metformin": "sugar", "Glimepirid": "sugar", "Empagliflozin": "sugar",
    "Dapagliflozin": "sugar", "Sitagliptin": "sugar",
    "Pantoprazol": "stomach", "Omeprazol": "stomach",
    "L-Thyroxin": "thyroid",
    "Paracetamol": "pain", "Ibuprofen": "pain", "Metamizol": "pain",
    "Allopurinol": "gout",
}

_LOWER = {name.lower(): name for name in DRUGS}


def canonical(name: str) -> str | None:
    """Exact (case-insensitive) match in the list, else None."""
    return _LOWER.get((name or "").strip().lower())


def suggest(name: str, cutoff: int = 80) -> str | None:
    """Closest known drug if the name looks misspelled. None if exact or unknown."""
    name = (name or "").strip()
    if not name or canonical(name):
        return None
    match = process.extractOne(name, list(DRUGS), scorer=fuzz.WRatio, score_cutoff=cutoff)
    return match[0] if match else None


def purpose(name: str) -> str | None:
    """Common-use category for a drug name (uses the first word, e.g. 'ASS 100')."""
    key = canonical(name) or canonical((name or "").split(" ")[0])
    return DRUGS.get(key) if key else None
