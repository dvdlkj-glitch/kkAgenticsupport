"""Inline the metallic textures as base64 data URIs into introduction.html.

Run after (re)writing web/introduction.html with the /*__ASSET_VARS__*/ marker.
Keeps the page self-contained so images render inside the Streamlit srcdoc iframe.
"""
import base64
import pathlib

root = pathlib.Path(__file__).resolve().parent          # web/
assets = root / "assets"

MAP = {
    "--img-chrome": "chrome-tall.jpg",   # big right panel
    "--img-disc":   "disc.jpg",          # left card 01
    "--img-metal4": "metal-4.jpg",       # left card 02
    "--img-metal2": "metal-2.jpg",       # left card 03
}


def datauri(name: str) -> str:
    b = (assets / name).read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(b).decode()


lines = ":root{\n" + "".join(
    f"  {var}:url('{datauri(f)}');\n" for var, f in MAP.items()
) + "}"

html_path = root / "introduction.html"
html = html_path.read_text(encoding="utf-8")
assert "/*__ASSET_VARS__*/" in html, "placeholder /*__ASSET_VARS__*/ missing"
html = html.replace("/*__ASSET_VARS__*/", lines, 1)
html_path.write_text(html, encoding="utf-8")
print("injected", len(MAP), "textures; file size KB:", round(len(html) / 1024, 1))
