from __future__ import annotations
import json, sys, traceback
from config import SETTINGS
from ocr_engine import LocalPaddleOCR
from preprocess import iter_input_documents, load_document, preprocess_page, save_variants

def score_candidate(result, max_chars):
    coverage = len(result.text.strip()) / max_chars if max_chars else 0.0
    return SETTINGS.confidence_weight * result.average_confidence + SETTINGS.coverage_weight * coverage

def process_document(path, ocr):
    doc_name = path.stem
    clean_root = SETTINGS.cleaned_dir / doc_name
    out_root = SETTINGS.output_dir / doc_name
    clean_root.mkdir(parents=True, exist_ok=True)
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {path.name} ===")
    full_text_parts = []
    doc_summary = {"source_file": path.name, "pages": []}

    for page_num, page_img in load_document(path):
        variants = preprocess_page(page_img)
        variant_paths = save_variants(variants, clean_root / f"page_{page_num:03d}")

        candidates = {}
        for variant in SETTINGS.ocr_variants:
            try:
                print(f"Page {page_num} OCR: {variant}")
                candidates[variant] = ocr.recognize(variant_paths[variant])
            except Exception as e:
                print(f"  failed: {e}")

        if not candidates:
            raise RuntimeError(f"No OCR result for {path.name}, page {page_num}")

        max_chars = max(len(r.text.strip()) for r in candidates.values())
        scores = {name: score_candidate(r, max_chars) for name, r in candidates.items()}
        best_name = max(scores, key=scores.get)
        best = candidates[best_name]

        page_out = out_root / f"page_{page_num:03d}"
        page_out.mkdir(parents=True, exist_ok=True)

        for name, result in candidates.items():
            (page_out / f"{name}.txt").write_text(result.text, encoding="utf-8")
            (page_out / f"{name}.json").write_text(
                json.dumps(result.raw, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        (page_out / "BEST.txt").write_text(best.text, encoding="utf-8")

        summary = {
            "page": page_num,
            "best_variant": best_name,
            "average_confidence": best.average_confidence,
            "heuristic_score": scores[best_name],
            "character_count": len(best.text.strip()),
            "variants": {
                name: {
                    "average_confidence": r.average_confidence,
                    "character_count": len(r.text.strip()),
                    "heuristic_score": scores[name],
                }
                for name, r in candidates.items()
            },
        }

        (page_out / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        doc_summary["pages"].append(summary)
        full_text_parts.append(f"--- PAGE {page_num} ---\n{best.text}")
        print(f"BEST: {best_name} | confidence={best.average_confidence:.3f}")

    (out_root / "full_text.txt").write_text("\n\n".join(full_text_parts), encoding="utf-8")
    (out_root / "document_summary.json").write_text(
        json.dumps(doc_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Saved: {out_root / 'full_text.txt'}")

def main():
    for folder in (SETTINGS.input_dir, SETTINGS.cleaned_dir, SETTINGS.output_dir):
        folder.mkdir(parents=True, exist_ok=True)

    docs = list(iter_input_documents(SETTINGS.input_dir))
    if not docs:
        print("No files found in input_docs.")
        return 0

    print("Initializing local PaddleOCR...")
    ocr = LocalPaddleOCR()
    failed = []

    for doc in docs:
        try:
            process_document(doc, ocr)
        except Exception:
            failed.append(doc.name)
            traceback.print_exc()

    if failed:
        print("Failed:", ", ".join(failed))
        return 1

    print("All documents processed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
