import re
from typing import List, Tuple, Optional

import numpy as np
from PIL import Image, ImageFilter, ImageOps

try:
    import pytesseract
except ImportError:  # allow module import without OCR installed
    pytesseract = None

try:
    from azure.cognitiveservices.vision.computervision import ComputerVisionClient
    from msrest.authentication import CognitiveServicesCredentials
except Exception:
    ComputerVisionClient = None
    CognitiveServicesCredentials = None


def _preprocess(img: Image.Image, invert: bool = False, threshold: int = 160) -> Image.Image:
    # Convert to grayscale, optionally invert for dark UIs, increase contrast, resize, sharpen, binarize
    g = ImageOps.grayscale(img)
    if invert:
        g = ImageOps.invert(g)
    g = ImageOps.autocontrast(g)
    # Resize up to improve OCR on small fonts
    w, h = g.size
    scale = 2 if max(w, h) < 1600 else 1
    if scale > 1:
        g = g.resize((w*scale, h*scale), Image.Resampling.LANCZOS)
    # Sharpen
    g = g.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    # Global threshold (clamp 0-255)
    t = max(0, min(255, int(threshold)))
    g = g.point(lambda p: 255 if p > t else 0, mode='1')
    return g.convert('L')


def extract_multipliers_from_image(image_path: str, invert: bool = False, threshold: int = 160,
                                   backend: str = "local", endpoint: Optional[str] = None,
                                   key: Optional[str] = None) -> List[float]:
    """
    Perform OCR on the provided image and extract multiplier values formatted like '1.78x', '95x', etc.
    Returns a list of floats (>=1).
    """
    if pytesseract is None:
        raise RuntimeError("pytesseract is not installed. Install Tesseract OCR and pytesseract.")

    if backend == "azure":
        text = _azure_ocr_text(image_path, endpoint=endpoint, key=key)
    else:
        img = Image.open(image_path)
        img2 = _preprocess(img, invert=invert, threshold=threshold)
        # Segment into horizontal lines to avoid token fusion across rows
        lines = _segment_lines(img2)
        texts = []
        for crop in lines:
            try:
                txt = pytesseract.image_to_string(
                    crop,
                    config="--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789xX.,:"
                )
                texts.append(txt)
            except Exception:
                continue
        text = "\n".join(texts)

    # Regex: capture numbers possibly with decimal, followed by optional spaces and 'x'/'X'
    # Capture raw tokens including possible OCR-decimal variants (comma, middot) before x
    # Pattern allows optional colon separators often present in UI and optional spaces
    # Stricter pattern: require 'x' immediately after number, allow up to 2 decimals
    pattern = re.compile(r"\b(\d{1,3}(?:[\.,·]\d{1,2})?)\s*[xX]\b")
    matches = pattern.findall(text)

    vals = []
    for m in matches:
        raw = m.strip()
        # Normalize decimal separators
        num = raw.replace("·", ".").replace(",", ".")
        # Heuristic: only fix missing decimals for exactly 3 digits (e.g., 198 -> 1.98)
        if "." not in num:
            digits = re.sub(r"[^0-9]", "", num)
            if len(digits) == 3:
                num = digits[0] + "." + digits[1:]
            else:
                # Leave as-is for other lengths to avoid false merges like 5521.24
                num = digits
        try:
            v = float(num)
            if v >= 1:
                vals.append(v)
        except ValueError:
            continue
    # Deduplicate close values and sort
    vals = sorted(set([round(v, 2) for v in vals]))
    return vals


def _segment_lines(img: Image.Image) -> List[Image.Image]:
    """Segment image into horizontal line crops using a projection profile."""
    import numpy as np
    arr = np.array(img)
    # If image is RGB, convert to grayscale array
    if arr.ndim == 3:
        arr = arr.mean(axis=2)
    # In binarized image, text ~ 0 (black), background ~ 255 (white)
    # Compute horizontal projection of dark pixels
    proj = (arr < 200).sum(axis=1)
    # Identify runs where projection exceeds a small threshold
    thr = max(5, int(arr.shape[1] * 0.01))
    lines: List[Tuple[int,int]] = []
    in_run = False
    start = 0
    for i, v in enumerate(proj):
        if v > thr and not in_run:
            in_run = True
            start = i
        elif v <= thr and in_run:
            in_run = False
            end = i
            if end - start > 8:  # minimum height
                lines.append((start, end))
    if in_run:
        end = len(proj) - 1
        if end - start > 8:
            lines.append((start, end))
    crops: List[Image.Image] = []
    for (s, e) in lines:
        # Add small padding
        s2 = max(0, s - 2)
        e2 = min(arr.shape[0], e + 2)
        crop = img.crop((0, s2, img.width, e2))
        crops.append(crop)
    # Fallback: return the full image if segmentation fails
    return crops or [img]


def _azure_ocr_text(image_path: str, endpoint: Optional[str], key: Optional[str]) -> str:
    """Use Azure Computer Vision Read API to extract text from an image."""
    import os
    ep = endpoint or os.environ.get("AZURE_CV_ENDPOINT")
    k = key or os.environ.get("AZURE_CV_KEY")
    if not ep or not k:
        raise RuntimeError("Azure OCR requires AZURE_CV_ENDPOINT and AZURE_CV_KEY.")
    if ComputerVisionClient is None:
        raise RuntimeError("Azure Computer Vision client not available. Install azure-cognitiveservices-vision-computervision and msrest.")
    client = ComputerVisionClient(ep, CognitiveServicesCredentials(k))
    with open(image_path, "rb") as f:
        result = client.read_in_stream(f, raw=True)
    operation_location = result.headers.get("Operation-Location")
    if not operation_location:
        return ""
    operation_id = operation_location.split("/")[-1]
    import time
    for _ in range(30):
        read_result = client.get_read_result(operation_id)
        if read_result.status not in ["notStarted", "running"]:
            if read_result.status == "succeeded":
                lines = []
                for rr in read_result.analyze_result.read_results:
                    for l in rr.lines:
                        lines.append(l.text)
                return "\n".join(lines)
            break
        time.sleep(0.4)
    return ""


def append_to_csv(csv_path: str, multipliers: List[float], session_id: str = "OCR") -> None:
    import pandas as pd
    df = pd.DataFrame({"session_id": session_id, "multiplier": multipliers})
    # append with header if file doesn't exist
    try:
        existing = pd.read_csv(csv_path)
        out = pd.concat([existing, df], ignore_index=True)
    except FileNotFoundError:
        out = df
    out.to_csv(csv_path, index=False)


def ocr_then_fit(image_path: str, csv_out: str | None = None):
    vals = extract_multipliers_from_image(image_path)
    if not vals:
        return {"extracted": [], "message": "No multipliers detected in image."}
    if csv_out:
        append_to_csv(csv_out, vals)
    return {"extracted": vals, "message": f"Extracted {len(vals)} values."}
