"""
Generate the RZ branding assets used by the Windows installers.

Outputs (all written next to this file's parent under ``assets/``):

    rz_icon.ico            — multi-resolution Windows icon (16, 24, 32, 48,
                             64, 128, 256). Used as the .exe icon and the
                             Inno-Setup ``SetupIconFile``.
    rz_logo_256.png        — 256×256 source PNG (debugging / preview).
    wizard_large.bmp       — 164×314 left-strip image for Inno Setup
                             ``WizardImageFile``.
    wizard_small.bmp       — 55×55 top-right image for Inno Setup
                             ``WizardSmallImageFile``.

Design language matches the QML dashboard:
    primary blue   #2563eb
    primary dark   #1d4ed8
    text white     #ffffff
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    print(
        "ERROR: Pillow is required. Install with:\n"
        "    pip install pillow",
        file=sys.stderr,
    )
    sys.exit(1)


HERE       = Path(__file__).resolve().parent
ASSETS_DIR = HERE.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ── Brand palette ───────────────────────────────────────────────────────
BLUE        = (37,  99, 235)   # #2563eb
BLUE_DARK   = (29,  78, 216)   # #1d4ed8
BLUE_DEEP   = (15,  17,  23)   # #0f1117  (UI app background)
WHITE       = (255, 255, 255)
WHITE_SOFT  = (226, 232, 240)  # #e2e8f0


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────
def _font(size: int) -> ImageFont.FreeTypeFont:
    """Pick a bold sans-serif that exists on the build machine."""
    candidates = [
        "segoeuib.ttf",          # Segoe UI Bold (Windows)
        "seguibl.ttf",           # Segoe UI Black (Windows)
        "arialbd.ttf",           # Arial Bold (Windows)
        "DejaVuSans-Bold.ttf",   # Linux fallback
        "Helvetica-Bold.ttf",    # macOS fallback
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    # Last resort: Pillow's default bitmap font (low quality, but never fails).
    return ImageFont.load_default()


def _rounded_gradient_square(size: int, radius_frac: float = 0.22) -> Image.Image:
    """Square with a diagonal blue gradient and rounded corners."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # 1. Vertical gradient from BLUE (top) to BLUE_DARK (bottom).
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(BLUE[0] * (1 - t) + BLUE_DARK[0] * t)
        g = int(BLUE[1] * (1 - t) + BLUE_DARK[1] * t)
        b = int(BLUE[2] * (1 - t) + BLUE_DARK[2] * t)
        grad.putpixel((0, y), (r, g, b))
    grad = grad.resize((size, size))

    # 2. Rounded-corner mask.
    mask = Image.new("L", (size, size), 0)
    radius = int(size * radius_frac)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=radius, fill=255
    )

    img.paste(grad, (0, 0), mask)
    return img


def _draw_rz(img: Image.Image, *, padding_frac: float = 0.16) -> None:
    """Draw the 'RZ' monogram centred on a square image, white on blue."""
    W, H = img.size
    pad  = int(min(W, H) * padding_frac)

    # Pick the font size that makes 'RZ' fill the inner box.
    target_w = W - 2 * pad
    target_h = H - 2 * pad
    fsize = max(8, int(H * 0.62))
    font = _font(fsize)
    while fsize > 8:
        font = _font(fsize)
        bbox = font.getbbox("RZ")
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= target_w and text_h <= target_h:
            break
        fsize -= 2

    bbox = font.getbbox("RZ")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (W - text_w) // 2 - bbox[0]
    y = (H - text_h) // 2 - bbox[1]

    draw = ImageDraw.Draw(img)
    # Soft drop shadow for depth.
    shadow_offset = max(1, W // 96)
    shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow_layer).text(
        (x + shadow_offset, y + shadow_offset), "RZ",
        font=font, fill=(0, 0, 0, 90),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=max(1, W // 128)))
    img.alpha_composite(shadow_layer)

    # Main glyph.
    draw.text((x, y), "RZ", font=font, fill=WHITE)


# ──────────────────────────────────────────────────────────────────────
# Public builders
# ──────────────────────────────────────────────────────────────────────
def build_icon_png(size: int = 256) -> Image.Image:
    img = _rounded_gradient_square(size)
    _draw_rz(img)
    return img


def build_ico(out_path: Path) -> None:
    """Multi-resolution .ico — Windows picks the best size for each context."""
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base  = build_icon_png(512)  # high-res master, then downscale
    images = []
    for s in sizes:
        images.append(base.resize((s, s), Image.LANCZOS))
    images[0].save(out_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"[icon]  wrote {out_path}  ({len(sizes)} resolutions)")


def build_wizard_large(out_path: Path) -> None:
    """164×314 BMP — left vertical strip on Inno's wizard pages."""
    W, H = 164, 314
    img = Image.new("RGB", (W, H), BLUE_DEEP)

    # Background: vertical gradient (deep navy → blue).
    for y in range(H):
        t = y / (H - 1)
        r = int(BLUE_DEEP[0] * (1 - t) + BLUE_DARK[0] * t)
        g = int(BLUE_DEEP[1] * (1 - t) + BLUE_DARK[1] * t)
        b = int(BLUE_DEEP[2] * (1 - t) + BLUE_DARK[2] * t)
        for x in range(W):
            img.putpixel((x, y), (r, g, b))

    # Top: the rounded RZ badge, centred horizontally.
    badge = build_icon_png(112)
    img.paste(badge, ((W - 112) // 2, 28), badge)

    # Tagline.
    draw = ImageDraw.Draw(img)
    title_font    = _font(20)
    subtitle_font = _font(11)

    title = "DroneResearch"
    bb = title_font.getbbox(title)
    draw.text(((W - (bb[2] - bb[0])) // 2, 160), title,
              font=title_font, fill=WHITE)

    sub = "UAV Research Platform"
    bb = subtitle_font.getbbox(sub)
    draw.text(((W - (bb[2] - bb[0])) // 2, 190), sub,
              font=subtitle_font, fill=WHITE_SOFT)

    img.save(out_path, format="BMP")
    print(f"[wizard] wrote {out_path}  (large 164×314)")


def build_wizard_small(out_path: Path) -> None:
    """55×55 BMP — top-right corner on Inno's wizard pages."""
    img = build_icon_png(110).convert("RGB").resize((55, 55), Image.LANCZOS)
    img.save(out_path, format="BMP")
    print(f"[wizard] wrote {out_path}  (small 55×55)")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────
def main() -> int:
    print(f"Generating RZ branding assets in: {ASSETS_DIR}")
    build_icon_png(256).save(ASSETS_DIR / "rz_logo_256.png")
    print(f"[png]   wrote {ASSETS_DIR / 'rz_logo_256.png'}")

    build_ico(ASSETS_DIR / "rz_icon.ico")
    build_wizard_large(ASSETS_DIR / "wizard_large.bmp")
    build_wizard_small(ASSETS_DIR / "wizard_small.bmp")

    print("\nAll assets generated. Re-run this script whenever the brand "
          "design changes; both installers pick the assets up automatically.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
