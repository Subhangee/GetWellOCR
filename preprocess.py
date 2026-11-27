from pathlib import Path
import cv2
import numpy as np
import pymupdf


# --------------------------------------------------
# FOLDERS
# --------------------------------------------------

INPUT_DIR = Path("input_docs")
OUTPUT_DIR = Path("cleaned_docs")

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# PDF -> IMAGES
# --------------------------------------------------

def pdf_to_images(pdf_path, dpi=300):

    doc = pymupdf.open(pdf_path)

    images = []

    zoom = dpi / 72
    matrix = pymupdf.Matrix(zoom, zoom)

    for page_number, page in enumerate(doc):

        pix = page.get_pixmap(
            matrix=matrix,
            alpha=False
        )

        image = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        )

        image = image.reshape(
            pix.height,
            pix.width,
            pix.n
        )

        image = cv2.cvtColor(
            image,
            cv2.COLOR_RGB2BGR
        )

        images.append(
            (page_number + 1, image)
        )

    doc.close()

    return images


# --------------------------------------------------
# LOAD PDF OR IMAGE
# --------------------------------------------------

def load_document(file_path):

    if file_path.suffix.lower() == ".pdf":

        return pdf_to_images(file_path)

    image = cv2.imread(str(file_path))

    if image is None:
        raise ValueError(
            f"Could not read: {file_path}"
        )

    return [(1, image)]


# --------------------------------------------------
# PREPROCESS IMAGE
# --------------------------------------------------

def preprocess(image):

    # Convert to grayscale
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # Remove some noise
    denoised = cv2.fastNlMeansDenoising(
        gray,
        None,
        7,
        7,
        21
    )

    # CLAHE contrast enhancement
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    clahe_image = clahe.apply(
        denoised
    )

    # Sharpen
    blurred = cv2.GaussianBlur(
        clahe_image,
        (0, 0),
        1.5
    )

    sharpened = cv2.addWeighted(
        clahe_image,
        1.6,
        blurred,
        -0.6,
        0
    )

    # Remove uneven background
    background = cv2.GaussianBlur(
        gray,
        (0, 0),
        25
    )

    normalized = cv2.divide(
        gray,
        background,
        scale=255
    )

    normalized = clahe.apply(
        normalized
    )

    # Adaptive threshold
    adaptive = cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    return {
        "original": image,
        "gray": gray,
        "clahe": clahe_image,
        "sharpened": sharpened,
        "normalized": normalized,
        "adaptive": adaptive
    }


# --------------------------------------------------
# PROCESS ALL FILES
# --------------------------------------------------

for file_path in INPUT_DIR.iterdir():

    if file_path.suffix.lower() not in [
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff"
    ]:
        continue

    print("\nProcessing:", file_path.name)

    pages = load_document(
        file_path
    )

    document_folder = (
        OUTPUT_DIR /
        file_path.stem
    )

    for page_number, image in pages:

        page_folder = (
            document_folder /
            f"page_{page_number}"
        )

        page_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        images = preprocess(
            image
        )

        for name, result in images.items():

            output_path = (
                page_folder /
                f"{name}.png"
            )

            cv2.imwrite(
                str(output_path),
                result
            )

            print(
                "Saved:",
                output_path
            )


print("\nFinished.")