"""One-time helper: turn a portrait photo into ascii.txt.

usage: python make_ascii.py photo.jpg [--cols 130] [--gamma 1.0]
                            [--box left,top,right,bottom] [--keep-bg]

Needs Pillow, plus rembg for background removal (pip install "rembg[cpu]").
The subject is cut out, sharpened and given local contrast (CLAHE, needs
opencv-python-headless; falls back to equalize) so facial features survive.
Brighter pixels -> denser glyphs; generate.py also dims sparse glyphs.
"""
import argparse
from PIL import Image, ImageOps, ImageFilter

from generate import RAMP


def local_contrast(gray, alpha):
    """CLAHE if OpenCV is available (pulls detail out of shadows), else equalize."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return ImageOps.equalize(gray, mask=alpha)
    g = np.array(gray)
    g = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(g)
    m = np.array(alpha) > 110
    lo, hi = np.percentile(g[m], (1, 99))
    g = np.clip((g.astype(float) - lo) / max(hi - lo, 1) * 255, 0, 255).astype("uint8")
    return Image.fromarray(g)


def cutout(src, keep_bg=False):
    img = Image.open(src).convert("RGB")
    if keep_bg:
        return img.convert("RGBA")
    from rembg import remove
    return remove(img)


def convert(cut, cols=130, gamma=1.0, box=None):
    """cut: RGBA image whose alpha marks the subject."""
    if box:
        cut = cut.crop(box)
    alpha = cut.split()[3]
    gray = cut.convert("L").filter(ImageFilter.UnsharpMask(radius=4, percent=120, threshold=2))
    gray = local_contrast(gray, alpha)
    w, h = gray.size
    rows = int(cols * h / w * 0.5)  # monospace cells are ~2x taller than wide
    gray = gray.resize((cols, rows), Image.LANCZOS)
    alpha = alpha.resize((cols, rows), Image.LANCZOS)
    lines = []
    for y in range(rows):
        line = ""
        for x in range(cols):
            if alpha.getpixel((x, y)) < 110:
                line += " "
                continue
            v = (gray.getpixel((x, y)) / 255) ** gamma
            line += RAMP[max(1, min(int(v * len(RAMP)), len(RAMP) - 1))]
        lines.append(line.rstrip())
    return lines


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("photo")
    p.add_argument("-o", "--out", default="ascii.txt")
    p.add_argument("--cols", type=int, default=130)
    p.add_argument("--gamma", type=float, default=1.0)
    p.add_argument("--box", type=lambda s: tuple(int(v) for v in s.split(",")))
    p.add_argument("--keep-bg", action="store_true")
    a = p.parse_args()
    lines = convert(cutout(a.photo, a.keep_bg), a.cols, a.gamma, a.box)
    with open(a.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {a.out} ({a.cols}x{len(lines)})")
