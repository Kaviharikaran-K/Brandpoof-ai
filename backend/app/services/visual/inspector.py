from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.analysis.common import (
    CATEGORY_ACCESSIBILITY,
    CATEGORY_VISUAL,
    SEVERITY_INFO,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    make_finding_id,
)
from app.services.visual.colour import (
    chroma,
    contrast_ratio,
    delta_e_hex,
    hex_to_rgb,
    is_near_neutral,
    rgb_to_hex,
    rgb_to_lab,
)

try:
    import numpy as np
    from PIL import Image, ImageOps

    PIXEL_ANALYSIS = True
except Exception:  # pragma: no cover - exercised only when deps are missing
    np = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    PIXEL_ANALYSIS = False

MATCH_DELTA_E = 10.0
DEVIATION_DELTA_E = 15.0
CLEAR_DEVIATION_DELTA_E = 25.0
LOGO_MATCH_THRESHOLD = 0.55
LOGO_UNCERTAIN_THRESHOLD = 0.3
MAX_ANALYSIS_PIXELS = 160
MAX_PALETTE_FINDINGS = 2

SUBJECTIVE_NOTE = (
    "Automated visual checks compare measured values with approved brand assets. Subjective design "
    "quality (aesthetics, composition, brand feel) cannot be objectively judged; anything labelled "
    "'Requires human review' needs a designer's judgement."
)


def _finding(
    *,
    category: str,
    severity: str,
    detected_text: str,
    explanation: str,
    correction: str | None,
    confidence: str,
    needs_human_review: bool,
    evidence: dict[str, Any],
) -> dict:
    return {
        "finding_id": make_finding_id(),
        "category": category,
        "severity": severity,
        "detected_text": detected_text,
        "start_offset": 0,
        "end_offset": 0,
        "evidence": evidence,
        "explanation": explanation,
        "suggested_correction": correction,
        "confidence": confidence,
        "review_status": "open",
        "requires_clarification": False,
        "needs_human_review": needs_human_review,
    }


def ocr_available() -> bool:
    if not PIXEL_ANALYSIS:
        return False
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def extract_ocr_text(image_path: Path) -> str | None:
    if not ocr_available():
        return None
    try:
        import pytesseract

        with Image.open(image_path) as img:
            img = ImageOps.exif_transpose(img)
            text = pytesseract.image_to_string(img)
        cleaned = " ".join(text.split())
        return cleaned or None
    except Exception:
        return None


def _dominant_colours(img: "Image.Image", limit: int = 5) -> list[dict]:
    small = img.copy()
    small.thumbnail((MAX_ANALYSIS_PIXELS, MAX_ANALYSIS_PIXELS))
    rgba = small.convert("RGBA")
    arr = np.asarray(rgba, dtype=np.int16)
    pixels = arr.reshape(-1, 4)
    opaque = pixels[pixels[:, 3] >= 128]
    if opaque.shape[0] == 0:
        return []
    quantised = (opaque[:, :3] // 24) * 24
    keys, inverse, counts = np.unique(
        quantised, axis=0, return_inverse=True, return_counts=True
    )
    sums = np.zeros((keys.shape[0], 3), dtype=np.float64)
    np.add.at(sums, inverse, opaque[:, :3])
    order = np.argsort(counts)[::-1]
    total = float(opaque.shape[0])
    result: list[dict] = []
    seen: list[tuple[int, int, int]] = []
    for index in order:
        mean = sums[index] / counts[index]
        rgb = tuple(int(round(c)) for c in mean)
        if any(delta_e_hex(rgb_to_hex(rgb), rgb_to_hex(existing)) < 6.0 for existing in seen):
            continue
        seen.append(rgb)
        lab = rgb_to_lab(rgb)
        result.append(
            {
                "hex": rgb_to_hex(rgb),
                "rgb": rgb,
                "share": round(float(counts[index]) / total, 4),
                "chroma": round(chroma(lab), 2),
            }
        )
        if len(result) >= limit:
            break
    return result


def _slide_views(image, template, step: int):
    windows = np.lib.stride_tricks.sliding_window_view(image, template.shape)
    return windows[::step, ::step]


def _logo_score(img: "Image.Image", logo_path: Path) -> dict | None:
    try:
        with Image.open(logo_path) as logo_img:
            logo_img = ImageOps.exif_transpose(logo_img).convert("RGBA")
            logo_small = logo_img.copy()
            logo_small.thumbnail((96, 96))
            logo_arr = np.asarray(logo_small, dtype=np.float32)
            alpha = logo_arr[:, :, 3] / 255.0
            weights = (alpha >= 0.4).astype(np.float32)
            if weights.sum() < 12:
                weights = np.ones_like(weights)
            grey_logo = (
                logo_arr[:, :, 0] * 0.299 + logo_arr[:, :, 1] * 0.587 + logo_arr[:, :, 2] * 0.114
            )
            logo_h, logo_w = grey_logo.shape
            if logo_h < 4 or logo_w < 4:
                return None
            mean_logo = float((grey_logo * weights).sum() / weights.sum())
            centred_logo = (grey_logo - mean_logo) * weights
            logo_energy = float((centred_logo**2).sum())
            if logo_energy <= 1e-6:
                return None
            image_small = img.copy()
            image_small.thumbnail((MAX_ANALYSIS_PIXELS, MAX_ANALYSIS_PIXELS))
            grey_img = np.asarray(image_small.convert("RGB"), dtype=np.float32)
            grey_img = grey_img[:, :, 0] * 0.299 + grey_img[:, :, 1] * 0.587 + grey_img[:, :, 2] * 0.114
    except Exception:
        return None

    best: dict | None = None
    for scale in (0.12, 0.18, 0.25, 0.35):
        target_h = max(6, int(round(grey_img.shape[0] * scale)))
        ratio = logo_w / max(logo_h, 1)
        target_w = max(6, int(round(target_h * ratio)))
        if target_h >= grey_img.shape[0] or target_w >= grey_img.shape[1]:
            continue
        tpl = np.asarray(
            Image.fromarray(grey_logo.astype(np.float32)).resize((target_w, target_h), Image.BILINEAR),
            dtype=np.float32,
        )
        wgt = np.asarray(
            Image.fromarray((weights * 255).astype(np.float32)).resize(
                (target_w, target_h), Image.BILINEAR
            ),
            dtype=np.float32,
        )
        wgt = (wgt / 255.0 > 0.4).astype(np.float32)
        if wgt.sum() < 12:
            wgt = np.ones_like(tpl)
        tpl_mean = float((tpl * wgt).sum() / wgt.sum())
        tpl_centred = (tpl - tpl_mean) * wgt
        tpl_energy = float((tpl_centred**2).sum())
        if tpl_energy <= 1e-6:
            continue
        windows = _slide_views(grey_img, tpl, step=2)
        n_windows = windows.shape[0] * windows.shape[1]
        if n_windows == 0:
            continue
        flat = windows.reshape(n_windows, target_h, target_w)
        weight_sum = float(wgt.sum())
        weighted_sum = (flat * wgt).sum(axis=(1, 2))
        local_mean = weighted_sum / weight_sum
        centred = flat - local_mean[:, None, None]
        local_energy = float(0.0) + ((centred**2) * wgt).sum(axis=(1, 2))
        numerator = (centred * tpl_centred).sum(axis=(1, 2))
        denominator = np.sqrt(np.maximum(local_energy, 1e-6) * tpl_energy)
        scores = numerator / denominator
        index = int(np.argmax(scores))
        score = float(scores[index])
        position = (int(index // windows.shape[1]) * 2, int(index % windows.shape[1]) * 2)
        if best is None or score > best["score"]:
            best = {
                "score": round(score, 4),
                "scale": scale,
                "width": target_w,
                "height": target_h,
                "position": {"x": position[1], "y": position[0]},
            }
    return best


def _palette_findings(dominants: list[dict], palette: list[dict]) -> tuple[list[dict], list[dict]]:
    findings: list[dict] = []
    matches: list[dict] = []
    for entry in dominants:
        nearest = min(palette, key=lambda p: delta_e_hex(entry["hex"], p["hex"]))
        delta = delta_e_hex(entry["hex"], nearest["hex"])
        if delta <= MATCH_DELTA_E:
            verdict = "match"
        elif delta <= DEVIATION_DELTA_E:
            verdict = "close"
        else:
            verdict = "deviation"
        matches.append(
            {
                "hex": entry["hex"],
                "share": entry["share"],
                "nearest_hex": nearest["hex"],
                "nearest_name": nearest["name"],
                "delta_e": round(delta, 2),
                "verdict": verdict,
            }
        )
        if (
            verdict == "deviation"
            and entry["share"] >= 0.08
            and not is_near_neutral(entry["rgb"])
            and len(findings) < MAX_PALETTE_FINDINGS
        ):
            severity = SEVERITY_MAJOR if delta >= CLEAR_DEVIATION_DELTA_E else SEVERITY_MINOR
            uncertain = delta < CLEAR_DEVIATION_DELTA_E
            findings.append(
                _finding(
                    category=CATEGORY_VISUAL,
                    severity=severity,
                    detected_text=f"Colour {entry['hex']}",
                    explanation=(
                        f"The colour {entry['hex']} covers about {round(entry['share'] * 100)}% of the "
                        f"image. The closest approved colour is {nearest['name']} ({nearest['hex']}), "
                        f"a CIE76 colour difference of {round(delta, 1)} (differences above about 10 are "
                        "perceptible; above about 25 are clearly different)."
                    ),
                    correction=f"Use an approved palette colour such as {nearest['hex']}.",
                    confidence="high" if delta >= CLEAR_DEVIATION_DELTA_E else "medium",
                    needs_human_review=uncertain,
                    evidence={
                        "rule": "palette_deviation",
                        "measured_hex": entry["hex"],
                        "share": entry["share"],
                        "nearest_hex": nearest["hex"],
                        "nearest_name": nearest["name"],
                        "delta_e": round(delta, 2),
                        "space": "CIELAB D65 (CIE76)",
                    },
                )
            )
    return findings, matches


def _contrast_findings(dominants: list[dict]) -> tuple[list[dict], list[dict]]:
    findings: list[dict] = []
    pairs: list[dict] = []
    if len(dominants) < 2:
        return findings, pairs
    foreground = dominants[0]
    background = dominants[1]
    ratio = contrast_ratio(foreground["rgb"], background["rgb"])
    pairs.append(
        {
            "foreground": foreground["hex"],
            "background": background["hex"],
            "ratio": round(ratio, 2),
            "wcag_aa_normal": ratio >= 4.5,
            "wcag_aa_large": ratio >= 3.0,
        }
    )
    if ratio < 4.5:
        severity = SEVERITY_MAJOR if ratio < 3.0 else SEVERITY_MINOR
        findings.append(
            _finding(
                category=CATEGORY_ACCESSIBILITY,
                severity=severity,
                detected_text=f"Contrast {round(ratio, 2)}:1",
                explanation=(
                    f"The contrast ratio between the two most common colours ({foreground['hex']} on "
                    f"{background['hex']}) is {round(ratio, 2)}:1. WCAG 2.1 AA requires at least 4.5:1 "
                    "for normal text and 3:1 for large text. Whether these colours are actually used as "
                    "text and background cannot be determined automatically."
                ),
                correction="Increase contrast, or confirm the intended text/background pair manually.",
                confidence="low",
                needs_human_review=True,
                evidence={
                    "rule": "wcag_contrast",
                    "foreground": foreground["hex"],
                    "background": background["hex"],
                    "ratio": round(ratio, 2),
                    "wcag": "WCAG 2.1 AA",
                },
            )
        )
    return findings, pairs


def _alt_text_findings(alt_text: str | None) -> list[dict]:
    cleaned = (alt_text or "").strip()
    if not cleaned:
        return [
            _finding(
                category=CATEGORY_ACCESSIBILITY,
                severity=SEVERITY_MINOR,
                detected_text="Missing alt text",
                explanation=(
                    "The attached visual has no alt text. Alternative text gives screen-reader users an "
                    "equivalent description and is a baseline accessibility requirement."
                ),
                correction="Add concise alt text that describes the purpose of the image.",
                confidence="high",
                needs_human_review=False,
                evidence={"rule": "missing_alt_text"},
            )
        ]
    if len(cleaned) < 8:
        return [
            _finding(
                category=CATEGORY_ACCESSIBILITY,
                severity=SEVERITY_INFO,
                detected_text=cleaned,
                explanation=(
                    f'The alt text "{cleaned}" is very short. Alt text should describe the purpose of '
                    "the visual, not just name it."
                ),
                correction="Expand the alt text to describe what the image communicates.",
                confidence="medium",
                needs_human_review=True,
                evidence={"rule": "brief_alt_text", "length": len(cleaned)},
            )
        ]
    return []


@dataclass
class VisualInspection:
    report: dict
    findings: list[dict] = field(default_factory=list)
    ocr_text: str | None = None
    analysed: bool = False


def inspect_image(
    image_path: Path | None,
    *,
    content_type: str | None = None,
    alt_text: str | None = None,
    palette: list[dict] | None = None,
    logo_path: Path | None = None,
) -> VisualInspection:
    palette = palette or []
    report: dict[str, Any] = {
        "available": False,
        "capabilities": {
            "pixel_analysis": PIXEL_ANALYSIS,
            "ocr": False,
            "logo_match": False,
            "palette_configured": bool(palette),
            "logo_configured": logo_path is not None and logo_path.exists(),
        },
        "limitations": [],
        "note": SUBJECTIVE_NOTE,
        "image": {},
        "dominant_colours": [],
        "palette_matches": [],
        "contrast": [],
        "logo": {"checked": False, "matched": None, "best_score": None},
    }
    findings = _alt_text_findings(alt_text)

    if image_path is None or not image_path.exists():
        report["limitations"].append("No visual was attached to this submission.")
        return VisualInspection(report=report, findings=findings, analysed=False)

    if not PIXEL_ANALYSIS:
        report["limitations"].append(
            "Image analysis libraries (numpy/Pillow) are not installed, so no pixel checks were run. "
            "Requires human review."
        )
        findings.append(
            _finding(
                category=CATEGORY_VISUAL,
                severity=SEVERITY_INFO,
                detected_text="Automated visual checks unavailable",
                explanation=(
                    "The server cannot run automated visual checks because the image analysis "
                    "libraries are unavailable. The attached visual requires human review."
                ),
                correction=None,
                confidence="low",
                needs_human_review=True,
                evidence={"rule": "pixel_analysis_unavailable"},
            )
        )
        return VisualInspection(report=report, findings=findings, analysed=False)

    is_svg = (content_type or "").lower() == "image/svg+xml" or image_path.suffix.lower() == ".svg"
    if is_svg:
        report["limitations"].append(
            "SVG files are not rasterised on the server; pixel checks (colour, contrast, logo) were "
            "skipped. Requires human review."
        )
        findings.append(
            _finding(
                category=CATEGORY_VISUAL,
                severity=SEVERITY_INFO,
                detected_text="SVG visual skipped",
                explanation=(
                    "This visual is an SVG and was not rasterised, so colour, contrast and logo checks "
                    "did not run. A designer should review it against the brand assets."
                ),
                correction=None,
                confidence="low",
                needs_human_review=True,
                evidence={"rule": "svg_not_analysed"},
            )
        )
        return VisualInspection(report=report, findings=findings, analysed=False)

    try:
        with Image.open(image_path) as opened:
            img = ImageOps.exif_transpose(opened).convert("RGB")
            width, height = img.size
            img.thumbnail((MAX_ANALYSIS_PIXELS, MAX_ANALYSIS_PIXELS))
        report["available"] = True
        report["image"] = {
            "width": width,
            "height": height,
            "format": (content_type or image_path.suffix.lstrip(".")).lower(),
        }
    except Exception:
        report["limitations"].append(
            "The attached image could not be decoded (it may be corrupt or unsupported). Requires "
            "human review."
        )
        findings.append(
            _finding(
                category=CATEGORY_VISUAL,
                severity=SEVERITY_INFO,
                detected_text="Image could not be decoded",
                explanation=(
                    "The file could not be opened as an image, so no visual checks ran. The visual "
                    "requires human review."
                ),
                correction=None,
                confidence="low",
                needs_human_review=True,
                evidence={"rule": "image_decode_failed"},
            )
        )
        return VisualInspection(report=report, findings=findings, analysed=False)

    dominants = _dominant_colours(img)
    report["dominant_colours"] = [
        {"hex": entry["hex"], "share": entry["share"]} for entry in dominants
    ]

    if palette:
        palette_findings, matches = _palette_findings(dominants, palette)
        findings.extend(palette_findings)
        report["palette_matches"] = matches
    else:
        report["limitations"].append(
            "No approved brand colours are configured, so palette checks were skipped. Requires human "
            "review of colour fidelity."
        )

    contrast_findings, contrast_pairs = _contrast_findings(dominants)
    findings.extend(contrast_findings)
    report["contrast"] = contrast_pairs

    if logo_path is not None and logo_path.exists():
        report["capabilities"]["logo_match"] = True
        logo_result = _logo_score(img, logo_path)
        if logo_result is not None:
            matched = logo_result["score"] >= LOGO_MATCH_THRESHOLD
            report["logo"] = {
                "checked": True,
                "matched": matched,
                "best_score": logo_result["score"],
                "threshold": LOGO_MATCH_THRESHOLD,
                "scale": logo_result["scale"],
            }
            if not matched:
                uncertain = logo_result["score"] >= LOGO_UNCERTAIN_THRESHOLD
                findings.append(
                    _finding(
                        category=CATEGORY_VISUAL,
                        severity=SEVERITY_MINOR if uncertain else SEVERITY_MAJOR,
                        detected_text="Approved logo not detected",
                        explanation=(
                            "Template matching against the approved logo produced a best normalised "
                            f"correlation of {logo_result['score']} (match threshold "
                            f"{LOGO_MATCH_THRESHOLD}). "
                            + (
                                "The score is close to the threshold, so the logo may be cropped, "
                                "rotated or recoloured; this requires human review."
                                if uncertain
                                else "The approved logo does not appear to be present in the visual."
                            )
                        ),
                        correction="Place the approved logo on the visual, in an approved colourway.",
                        confidence="low" if uncertain else "medium",
                        needs_human_review=True,
                        evidence={
                            "rule": "logo_presence",
                            "best_score": logo_result["score"],
                            "threshold": LOGO_MATCH_THRESHOLD,
                            "method": "masked normalised cross-correlation",
                        },
                    )
                )
    else:
        report["limitations"].append(
            "No approved logo is configured, so logo presence was not checked. Requires human review."
        )

    ocr_ready = ocr_available()
    report["capabilities"]["ocr"] = ocr_ready
    ocr_text = extract_ocr_text(image_path) if ocr_ready else None
    if ocr_ready:
        if ocr_text:
            report["limitations"].append(
                "Text inside the image was extracted with OCR; OCR can misread characters, so those "
                "claims require human review."
            )
        else:
            report["limitations"].append(
                "OCR found no readable text in the image (or the image has none)."
            )
    else:
        report["limitations"].append(
            "OCR (Tesseract) is not installed, so text inside the image was not checked. Requires "
            "human review."
        )
        findings.append(
            _finding(
                category=CATEGORY_VISUAL,
                severity=SEVERITY_INFO,
                detected_text="Text in image not checked",
                explanation=(
                    "The server has no OCR engine, so any text embedded in the visual was not verified "
                    "against the approved facts. A reviewer should check it manually."
                ),
                correction=None,
                confidence="low",
                needs_human_review=True,
                evidence={"rule": "ocr_unavailable"},
            )
        )

    return VisualInspection(
        report=report,
        findings=findings,
        ocr_text=ocr_text,
        analysed=True,
    )
