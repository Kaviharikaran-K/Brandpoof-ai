import io

from PIL import Image, ImageDraw

from app.services.visual import inspect_image
from tests.conftest import fact_payload, register, switch_user

ADMIN = "admin@visual.example.com"
CREATOR = "creator@visual.example.com"
PASSWORD = "Password123!"


def _png(colour: tuple[int, int, int], size: tuple[int, int] = (240, 180)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, format="PNG")
    return buffer.getvalue()


def _logo_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), (15, 118, 110))
    draw = ImageDraw.Draw(img)
    draw.rectangle([18, 14, 28, 50], fill=(247, 245, 240))
    draw.rectangle([18, 14, 46, 24], fill=(247, 245, 240))
    draw.rectangle([18, 30, 42, 38], fill=(247, 245, 240))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_palette_deviation_is_measured_and_major(tmp_path):
    image_path = tmp_path / "red.png"
    image_path.write_bytes(_png((180, 35, 42)))
    result = inspect_image(
        image_path,
        content_type="image/png",
        alt_text="Red promotion banner",
        palette=[{"name": "Brand teal", "hex": "#0F766E"}],
    )
    assert result.analysed is True
    assert result.report["available"] is True
    assert result.report["dominant_colours"][0]["hex"] == "#B4232A"
    assert result.report["palette_matches"][0]["nearest_hex"] == "#0F766E"
    assert result.report["palette_matches"][0]["delta_e"] > 25
    finding = next(f for f in result.findings if f["category"] == "Visual inconsistency")
    assert finding["severity"] == "Major"
    assert finding["evidence"]["rule"] == "palette_deviation"
    assert finding["evidence"]["measured_hex"] == "#B4232A"
    assert finding["needs_human_review"] is False
    assert "CIE76" in finding["evidence"]["space"]


def test_missing_alt_text_is_accessibility_finding(tmp_path):
    image_path = tmp_path / "plain.png"
    image_path.write_bytes(_png((247, 245, 240)))
    result = inspect_image(image_path, content_type="image/png", alt_text=None)
    finding = next(f for f in result.findings if f["detected_text"] == "Missing alt text")
    assert finding["category"] == "Accessibility issue"
    assert finding["severity"] == "Minor"
    assert finding["needs_human_review"] is False
    assert any("No approved brand colours" in note for note in result.report["limitations"])


def test_low_contrast_is_flagged_for_human_review(tmp_path):
    image_path = tmp_path / "contrast.png"
    img = Image.new("RGB", (200, 120), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 0, 200, 120], fill=(128, 128, 128))
    img.save(image_path)
    result = inspect_image(image_path, content_type="image/png", alt_text="Split banner")
    contrast = result.report["contrast"][0]
    assert contrast["ratio"] < 4.5
    finding = next(f for f in result.findings if f["category"] == "Accessibility issue")
    assert finding["evidence"]["rule"] == "wcag_contrast"
    assert finding["needs_human_review"] is True


def test_logo_presence_is_matched_against_approved_logo(tmp_path):
    logo_path = tmp_path / "logo.png"
    logo_path.write_bytes(_logo_bytes())
    canvas = Image.new("RGB", (320, 240), (247, 245, 240))
    logo = Image.open(io.BytesIO(_logo_bytes())).resize((64, 64))
    canvas.paste(logo, (235, 18))
    image_path = tmp_path / "ad.png"
    canvas.save(image_path)

    result = inspect_image(
        image_path,
        content_type="image/png",
        alt_text="Advert with the approved logo",
        logo_path=logo_path,
    )
    assert result.report["logo"]["checked"] is True
    assert result.report["logo"]["matched"] is True
    assert result.report["logo"]["best_score"] >= result.report["logo"]["threshold"]
    assert not any(f["detected_text"] == "Approved logo not detected" for f in result.findings)


def test_svg_is_skipped_and_requires_human_review(tmp_path):
    image_path = tmp_path / "vector.svg"
    image_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>')
    result = inspect_image(image_path, content_type="image/svg+xml", alt_text=None)
    assert result.analysed is False
    assert result.report["available"] is False
    assert any("SVG" in note for note in result.report["limitations"])
    info = next(f for f in result.findings if f["detected_text"] == "SVG visual skipped")
    assert info["severity"] == "Information"
    assert info["needs_human_review"] is True


async def test_visual_inspection_runs_through_the_api(client):
    admin = await register(client, ADMIN, "Ann Admin")
    org_id = admin["memberships"][0]["org_id"]
    await register(client, CREATOR, "Carl Creator")
    await switch_user(client, ADMIN)
    await client.post(f"/api/organisations/{org_id}/members", json={"email": CREATOR, "role": "creator"})
    headers = {"X-Org-Id": str(org_id)}
    created_fact = await client.post("/api/brand/facts", json=fact_payload(), headers=headers)
    assert created_fact.status_code == 201
    await client.post(f"/api/brand/facts/{created_fact.json()['id']}/confirm", headers=headers)
    created_colour = await client.post(
        "/api/brand/assets/colours",
        json={"name": "Brand teal", "colour_value": "#0F766E"},
        headers=headers,
    )
    assert created_colour.status_code == 201

    await switch_user(client, CREATOR)
    created = await client.post(
        "/api/submissions",
        data={
            "title": "Visual launch ad",
            "submission_type": "ad_copy",
            "content": "NovaCloud supports 5,000 users.",
        },
        files={"image": ("ad.png", _png((180, 35, 42)), "image/png")},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    submission = created.json()
    assert submission["has_image"] is True
    assert submission["alt_text"] is None

    analysed = await client.post(f"/api/submissions/{submission['id']}/analyse", headers=headers)
    assert analysed.status_code == 200, analysed.text
    detail = analysed.json()
    run = detail["runs"][0]
    assert run["engine"].endswith("+ Visual")
    assert run["visual_report"]["available"] is True
    assert run["visual_report"]["palette_matches"][0]["delta_e"] > 25
    categories = {finding["category"] for finding in run["findings"]}
    assert "Visual inconsistency" in categories
    assert "Accessibility issue" in categories

    revised = await client.post(
        f"/api/submissions/{submission['id']}/revise",
        data={
            "content": "NovaCloud supports 5,000 users. Contact the customer team.",
            "alt_text": "Product dashboard shown on a teal background",
        },
        headers=headers,
    )
    assert revised.status_code == 200, revised.text
    revised_detail = revised.json()
    assert revised_detail["alt_text"] == "Product dashboard shown on a teal background"
    latest = revised_detail["runs"][0]
    assert not any(
        finding["detected_text"] == "Missing alt text" for finding in latest["findings"]
    )
