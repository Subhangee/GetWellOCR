from pathlib import Path
from paddleocr import PaddleOCR


# -----------------------------------------
# FOLDERS
# -----------------------------------------

CLEANED_DIR = Path("cleaned_docs")
OUTPUT_DIR = Path("ocr_output")

OUTPUT_DIR.mkdir(exist_ok=True)


# -----------------------------------------
# INITIALIZE OCR
# -----------------------------------------

ocr = PaddleOCR(
    lang="en",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False
)


# -----------------------------------------
# OCR ONE IMAGE
# -----------------------------------------

def read_image(image_path):

    results = ocr.predict(
        input=str(image_path)
    )

    text_lines = []
    confidences = []

    for result in results:

        data = result.json

        if "res" in data:
            data = data["res"]

        texts = data.get(
            "rec_texts",
            []
        )

        scores = data.get(
            "rec_scores",
            []
        )

        for text, score in zip(
            texts,
            scores
        ):
            text_lines.append(text)
            confidences.append(float(score))

    full_text = "\n".join(
        text_lines
    )

    if confidences:
        average_confidence = (
            sum(confidences)
            / len(confidences)
        )
    else:
        average_confidence = 0

    return (
        full_text,
        average_confidence
    )


# -----------------------------------------
# PROCESS CLEANED DOCUMENTS
# -----------------------------------------

for document_folder in CLEANED_DIR.iterdir():

    if not document_folder.is_dir():
        continue

    print(
        "\nDocument:",
        document_folder.name
    )

    document_output = (
        OUTPUT_DIR /
        document_folder.name
    )

    document_output.mkdir(
        parents=True,
        exist_ok=True
    )


    for page_folder in document_folder.iterdir():

        if not page_folder.is_dir():
            continue

        print(
            "\nPage:",
            page_folder.name
        )

        page_output = (
            document_output /
            page_folder.name
        )

        page_output.mkdir(
            parents=True,
            exist_ok=True
        )


        # Only test these three for now
        variants = [
            "clahe.png",
            "sharpened.png",
            "normalized.png"
        ]


        best_text = ""
        best_score = 0
        best_variant = ""


        for variant in variants:

            image_path = (
                page_folder /
                variant
            )

            if not image_path.exists():
                continue

            print(
                "OCR:",
                variant
            )

            text, confidence = read_image(
                image_path
            )

            print(
                "Confidence:",
                round(confidence, 3)
            )


            # Save each OCR result
            output_text_file = (
                page_output /
                variant.replace(
                    ".png",
                    ".txt"
                )
            )

            output_text_file.write_text(
                text,
                encoding="utf-8"
            )


            # Keep best result
            if confidence > best_score:

                best_score = confidence
                best_text = text
                best_variant = variant


        # Save best OCR text
        best_file = (
            page_output /
            "BEST.txt"
        )

        best_file.write_text(
            best_text,
            encoding="utf-8"
        )


        print(
            "\nBest:",
            best_variant
        )

        print(
            "Confidence:",
            round(best_score, 3)
        )


print(
    "\nOCR finished."
)