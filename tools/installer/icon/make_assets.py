"""
Generate the UAVResearch branding assets used by the Windows installers.

Outputs (all written under ``tools/installer/assets/``):

    uavresearch_icon.ico       — multi-resolution Windows icon (16..256 px)
    uavresearch_logo_256.png   — 256×256 source PNG (debugging / preview)
    wizard_large.bmp           — 164×314 left-strip image for Inno Setup
    wizard_small.bmp           — 55×55 top-right image for Inno Setup

The visual language matches the QML dashboard: deep blue gradients,
subtle glow, and an abstract drone / radar emblem without any text.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    print(
        "ERROR: Pillow is required. Install with:\n    pip install pillow",
        file=sys.stderr,
    )
    sys.exit(1)


HERE = Path(__file__).resolve().parent
ASSETS_DIR = HERE.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

BLUE = (37, 99, 235)  # #2563eb
BLUE_DARK = (29, 78, 216)  # #1d4ed8
BLUE_DEEP = (15, 17, 23)  # #0f1117
WHITE = (255, 255, 255)
WHITE_SOFT = (226, 232, 240)

if hasattr(Image, "Resampling"):
    RESAMPLING_LANCZOS = Image.Resampling.LANCZOS
else:
    RESAMPLING_LANCZOS = getattr(Image, "LANCZOS")


def _font(size: int) -> Any:
    candidates = [
        "segoeuib.ttf",
        "seguibl.ttf",
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf",
        "Helvetica-Bold.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _vertical_gradient(
    size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]
) -> Image.Image:
    width, height = size
    grad = Image.new("RGB", (1, height))
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        grad.putpixel((0, y), (r, g, b))
    return grad.resize((width, height))


def _rounded_gradient_square(size: int, radius_frac: float = 0.22) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    grad = _vertical_gradient((size, size), BLUE, BLUE_DARK)

    mask = Image.new("L", (size, size), 0)
    radius = int(size * radius_frac)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=radius, fill=255
    )

    img.paste(grad, (0, 0), mask)
    return img


def _draw_emblem(img: Image.Image) -> None:
    w, h = img.size
    cx, cy = w / 2, h / 2
    ring_r = min(w, h) * 0.24
    inner_r = ring_r * 0.42
    spoke_r = ring_r * 0.84
    hub_r = max(4, int(w * 0.03))
    rotor_r = max(4, int(w * 0.04))
    glow_r = max(rotor_r + 4, int(w * 0.06))

    # Soft background glow
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse(
        (cx - ring_r - 22, cy - ring_r - 22, cx + ring_r + 22, cy + ring_r + 22),
        fill=(147, 197, 253, 40),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(4, w // 42)))
    img.alpha_composite(glow)

    draw = ImageDraw.Draw(img)
    ring_width = max(2, int(w * 0.02))
    draw.ellipse(
        (cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r),
        outline=(191, 219, 254, 230),
        width=ring_width,
    )
    draw.ellipse(
        (
            cx - ring_r * 0.78,
            cy - ring_r * 0.78,
            cx + ring_r * 0.78,
            cy + ring_r * 0.78,
        ),
        outline=(147, 197, 253, 96),
        width=max(1, ring_width // 2),
    )

    for dx, dy in ((0, -spoke_r), (spoke_r, 0), (0, spoke_r), (-spoke_r, 0)):
        draw.line(
            (cx, cy, cx + dx, cy + dy), fill=(191, 219, 254, 220), width=ring_width
        )
        draw.ellipse(
            (cx + dx - glow_r, cy + dy - glow_r, cx + dx + glow_r, cy + dy + glow_r),
            fill=(96, 165, 250, 56),
        )
        draw.ellipse(
            (
                cx + dx - rotor_r,
                cy + dy - rotor_r,
                cx + dx + rotor_r,
                cy + dy + rotor_r,
            ),
            fill=(255, 255, 255, 236),
        )

    draw.ellipse(
        (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
        fill=(15, 23, 42, 170),
        outline=(191, 219, 254, 200),
        width=max(1, ring_width // 2),
    )
    draw.ellipse(
        (cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r),
        fill=WHITE,
    )


def build_icon_png(size: int = 256) -> Image.Image:
    img = _rounded_gradient_square(size)
    _draw_emblem(img)
    return img


def build_ico(out_path: Path) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base = build_icon_png(512)
    base.save(out_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"[icon]  wrote {out_path}  ({len(sizes)} resolutions)")


def build_wizard_large(out_path: Path) -> None:
    w, h = 164, 314
    img = _vertical_gradient((w, h), BLUE_DEEP, BLUE_DARK)

    badge = build_icon_png(112)
    img.paste(badge, ((w - 112) // 2, 28), badge)

    draw = ImageDraw.Draw(img)
    title_font = _font(17)
    subtitle_font = _font(11)

    title = "uavresearch gcs"
    bb = title_font.getbbox(title)
    draw.text(((w - (bb[2] - bb[0])) // 2, 162), title, font=title_font, fill=WHITE)

    sub = "Ground Control Station"
    bb = subtitle_font.getbbox(sub)
    draw.text(
        ((w - (bb[2] - bb[0])) // 2, 191), sub, font=subtitle_font, fill=WHITE_SOFT
    )

    img.save(out_path, format="BMP")
    print(f"[wizard] wrote {out_path}  (large 164×314)")


def build_wizard_small(out_path: Path) -> None:
    img = build_icon_png(110).convert("RGB").resize((55, 55), RESAMPLING_LANCZOS)
    img.save(out_path, format="BMP")
    print(f"[wizard] wrote {out_path}  (small 55×55)")


def main() -> int:
    print(f"Generating UAVResearch branding assets in: {ASSETS_DIR}")
    build_icon_png(256).save(ASSETS_DIR / "uavresearch_logo_256.png")
    print(f"[png]   wrote {ASSETS_DIR / 'uavresearch_logo_256.png'}")

    build_ico(ASSETS_DIR / "uavresearch_icon.ico")
    build_wizard_large(ASSETS_DIR / "wizard_large.bmp")
    build_wizard_small(ASSETS_DIR / "wizard_small.bmp")

    print(
        "\nAll assets generated. Re-run this script whenever the brand "
        "design changes; both installers pick the assets up automatically."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
