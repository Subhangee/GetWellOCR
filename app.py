"""paper2pc demo app.

Run from the project folder:   streamlit run app.py
Opens in your browser at http://localhost:8501
"""
import tempfile
from pathlib import Path

import cv2
import pandas as pd
import streamlit as st

from src import config
from src.export import LANGUAGES, patient_plan_pdf, to_csv, to_fhir, to_json
from src.extract import read_text
from src.parse import parse_lines
from src.preprocess import ALL_STEPS, load_image, preprocess
from src.review import (DX_FIELDS, MED_FIELDS, corrections, dx_rows, finalize_dx,
                        finalize_meds, med_rows, unchecked_flags)

st.set_page_config(page_title="paper2pc", page_icon="📄", layout="wide")
st.title("paper2pc")
st.caption("From paper to PC: medications and diagnoses in seconds. Demo with fictional data only.")

# ---------- sidebar ----------
with st.sidebar:
    st.header("Settings")
    engine = st.selectbox("OCR engine", ["tesseract", "azure"],
                          index=0 if config.OCR_ENGINE == "tesseract" else 1)
    steps = st.multiselect("Image cleanup steps", list(ALL_STEPS[1:]), default=list(ALL_STEPS[1:]))
    st.caption(f"Fields below {config.LOW_CONFIDENCE:.0%} confidence are flagged for review.")

# ---------- input: upload or sample ----------
col_up, col_sample = st.columns([3, 2])
uploaded = col_up.file_uploader("Upload a scan, photo or PDF", type=["png", "jpg", "jpeg", "pdf"])
samples = [*sorted(config.DATA_DIR.glob("cases/*/pages_photo/*.jpg")),
           *sorted(config.DEGRADED_DIR.glob("*.png")),
           *sorted((config.DATA_DIR / "handwritten").glob("*.*"))]
sample = col_sample.selectbox("…or pick a sample", ["(none)"] + [p.name for p in samples])

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded.name).suffix) as tmp:
        tmp.write(uploaded.getvalue())
    source, doc_id = tmp.name, Path(uploaded.name).stem
elif sample != "(none)":
    source = str(next(p for p in samples if p.name == sample))
    doc_id = Path(sample).stem
else:
    st.info("Upload a document or pick a sample to start.")
    st.stop()

# ---------- load + clean ----------
original = load_image(source)
cleaned, log = preprocess(original, steps=("gray", *steps))

col1, col2 = st.columns(2)
col1.subheader("Original")
col1.image(cv2.cvtColor(original, cv2.COLOR_BGR2RGB), width="stretch")
col2.subheader("Cleaned")
col2.image(cleaned, width="stretch")
col2.caption("Steps: " + " → ".join(log))

# ---------- extract ----------
if st.button("Extract medications and diagnoses", type="primary"):
    with st.spinner("Reading document..."):
        result = parse_lines(read_text(cleaned, engine), doc_id, engine)
    st.session_state.result = result
    st.session_state.image = cleaned
    st.session_state.med_rows = med_rows(result)
    st.session_state.dx_rows = dx_rows(result)
    st.session_state.med_orig = [dict(r) for r in st.session_state.med_rows]   # what the machine read
    st.session_state.dx_orig = [dict(r) for r in st.session_state.dx_rows]
    st.session_state.run = st.session_state.get("run", 0) + 1   # fresh editors per document

result = st.session_state.get("result")
if result is None:
    st.stop()

# ---------- highlight boxes on the page ----------
vis = cv2.cvtColor(st.session_state.image, cv2.COLOR_GRAY2BGR)
h, w = vis.shape[:2]
GREEN, BLUE, YELLOW = (60, 160, 60), (200, 120, 30), (0, 200, 255)


def draw(items, color, pad=8):
    for it in items:
        if it.bbox:
            low = it.confidence is not None and it.confidence < config.LOW_CONFIDENCE
            c = YELLOW if low else color
            top_left = (max(0, int(it.bbox.x0 * w) - pad), max(0, int(it.bbox.y0 * h) - pad))
            bottom_right = (min(w - 1, int(it.bbox.x1 * w) + pad), min(h - 1, int(it.bbox.y1 * h) + pad))
            cv2.rectangle(vis, top_left, bottom_right, c, 3)


draw(result.medications, GREEN)
draw(result.diagnoses, BLUE)
st.subheader("What was found")
st.image(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB), width="stretch",
         caption="Green = medication, blue = diagnosis, yellow = please check")

# ---------- doctor review ----------
st.subheader("Review and confirm")
st.markdown("Double-click a cell to correct it. Rows marked **⚠️ check** were read with low "
            "confidence: compare them with the page and tick **✓ checked**. "
            "Add missing drugs in the empty last row.")

MED_COLS = ["flag", "name", "suggestion", "use_suggestion", "strength", "form", "dosing",
            "as_needed", "status", "confidence", "checked"]
DX_COLS = ["flag", "text", "icd10", "confidence", "checked"]


def apply_edits(base: list[dict], delta: dict | None, cols: list[str]) -> list[dict]:
    """Rebuild the table as the user currently sees it (base rows + their edits)."""
    rows = [dict(r) for r in base]
    if not delta:
        return rows
    for i, changes in delta.get("edited_rows", {}).items():
        rows[int(i)].update(changes)
    for added in delta.get("added_rows", []):
        rows.append({c: added.get(c) for c in cols})
    for i in sorted(delta.get("deleted_rows", []), reverse=True):
        rows.pop(int(i))
    return rows


def tick_all(table: str, column: str):
    """Button callback: tick (or untick, if all are ticked) a whole checkbox column."""
    ss = st.session_state
    ss.med_rows = apply_edits(ss.med_rows, ss.get(f"meds_{ss.run}"), MED_COLS)
    ss.dx_rows = apply_edits(ss.dx_rows, ss.get(f"dx_{ss.run}"), DX_COLS)
    rows = ss.med_rows if table == "meds" else ss.dx_rows
    if column == "use_suggestion":
        targets = [r for r in rows if r.get("suggestion")]
    else:
        targets = rows
    value = not all(bool(r.get(column)) for r in targets) if targets else True
    for r in targets:
        r[column] = value
    ss.run += 1   # new editor key, so the table shows the updated rows


b1, b2, b3, _ = st.columns([1, 1, 1, 2])
b1.button("✓ Tick all drugs", on_click=tick_all, args=("meds", "checked"), width="stretch",
          help="Tick or untick the ✓ checked column for every drug")
b2.button("Use all suggestions", on_click=tick_all, args=("meds", "use_suggestion"), width="stretch",
          help="Accept every spelling suggestion (click again to undo)")
b3.button("✓ Tick all diagnoses", on_click=tick_all, args=("dx", "checked"), width="stretch")

run = st.session_state.run
med_df = st.data_editor(
    pd.DataFrame(st.session_state.med_rows, columns=MED_COLS),
    key=f"meds_{run}", num_rows="dynamic", width="stretch", hide_index=True,
    column_order=MED_COLS,
    column_config={
        "flag": st.column_config.TextColumn("", disabled=True, width="small"),
        "name": st.column_config.TextColumn("Drug"),
        "suggestion": st.column_config.TextColumn("Did you mean?", disabled=True,
                                                  help="Closest match in the drug list"),
        "use_suggestion": st.column_config.CheckboxColumn("Use it", help="Replace the name with the suggestion"),
        "strength": st.column_config.TextColumn("Strength"),
        "form": st.column_config.TextColumn("Form"),
        "dosing": st.column_config.TextColumn("Mo-Mi-Ab-Na", help="Morning-noon-evening-night, e.g. 1-0-1-0"),
        "as_needed": st.column_config.CheckboxColumn("b.B."),
        "status": st.column_config.SelectboxColumn("Status", options=["active", "new", "stopped", "paused"],
                                                   default="active"),
        "confidence": st.column_config.NumberColumn("Conf.", disabled=True, format="%.2f"),
        "checked": st.column_config.CheckboxColumn("✓ checked", default=False),
    },
)
dx_df = st.data_editor(
    pd.DataFrame(st.session_state.dx_rows, columns=DX_COLS),
    key=f"dx_{run}", num_rows="dynamic", width="stretch", hide_index=True,
    column_order=DX_COLS,
    column_config={
        "flag": st.column_config.TextColumn("", disabled=True, width="small"),
        "text": st.column_config.TextColumn("Diagnosis"),
        "icd10": st.column_config.TextColumn("ICD-10-GM"),
        "confidence": st.column_config.NumberColumn("Conf.", disabled=True, format="%.2f"),
        "checked": st.column_config.CheckboxColumn("✓ checked", default=False),
    },
)


def records(df: pd.DataFrame) -> list[dict]:
    """Table rows as plain dicts, with empty cells as None."""
    return df.astype(object).where(pd.notna(df), None).to_dict(orient="records")


med_now, dx_now = records(med_df), records(dx_df)
meds_final, dx_final = finalize_meds(med_now), finalize_dx(dx_now)
log_rows = (corrections(finalize_meds(st.session_state.med_orig), meds_final, MED_FIELDS, "name")
            + corrections(finalize_dx(st.session_state.dx_orig), dx_final, DX_FIELDS, "text"))
pending = unchecked_flags(med_now) + unchecked_flags(dx_now)

m1, m2, m3 = st.columns(3)
m1.metric("Medications", len(meds_final))
m2.metric("Still to check", pending)
m3.metric("Corrections made", len(log_rows))
for warning in result.warnings:
    st.warning(warning)

with st.expander(f"Correction log ({len(log_rows)})"):
    if log_rows:
        st.dataframe(pd.DataFrame(log_rows), width="stretch", hide_index=True)
    else:
        st.caption("No changes yet: the table matches what the machine read.")

# ---------- export ----------
st.subheader("Export")
if pending:
    st.warning(f"Please check {pending} flagged row(s) before exporting.")
locked = pending > 0

e1, e2, e3, e4 = st.columns(4)
e1.download_button("JSON", data=to_json(doc_id, meds_final, dx_final, log_rows),
                   file_name=f"{doc_id}_confirmed.json", mime="application/json",
                   disabled=locked, width="stretch")
e2.download_button("FHIR (draft R4)", data=to_fhir(doc_id, meds_final, dx_final),
                   file_name=f"{doc_id}_fhir.json", mime="application/fhir+json",
                   disabled=locked, width="stretch")
e3.download_button("CSV (Excel)", data=to_csv(meds_final),
                   file_name=f"{doc_id}_medications.csv", mime="text/csv",
                   disabled=locked, width="stretch")
with e4:
    lang = st.selectbox("Patient plan language", list(LANGUAGES), format_func=LANGUAGES.get)
    patient = st.text_input("Patient name (optional)", value="")
    plan_pdf = patient_plan_pdf(meds_final, lang, patient)
    st.download_button("Patient plan (PDF)", data=plan_pdf,
                       file_name=f"{doc_id}_plan_{lang}.pdf", mime="application/pdf",
                       disabled=locked, width="stretch")
st.caption("Patient-plan translations are fixed phrases; have a native speaker check them before real use.")

with st.expander(f"Preview patient plan ({LANGUAGES[lang]})", expanded=not locked):
    import pypdfium2 as pdfium
    page = pdfium.PdfDocument(plan_pdf)[0].render(scale=1.6).to_pil()
    st.image(page, width="stretch")
    if locked:
        st.caption("Preview only: the plan can be downloaded once all flagged rows are checked.")

with st.expander("Raw OCR text"):
    st.text(result.raw_text)
