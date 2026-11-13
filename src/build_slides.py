"""Génère la présentation Comex : livrables/Presentation_Produits_Frais.pdf (6 slides 16:9).
S'appuie sur les mêmes données que le dashboard. Nécessite Google Chrome pour l'export PDF (sinon, ouvrir
dashboard/slides.html dans un navigateur et imprimer en PDF, format 960 x 540 px, marges nulles)."""
from __future__ import annotations

import json
import shutil
import subprocess

from src.build_dashboard import DASH, build_payload, load_model
from src.common import ROOT

CHROME = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium"]


def main() -> None:
    payload = build_payload(load_model())
    html = ((DASH / "slides_template.html").read_text(encoding="utf-8")
            .replace("/*__CHARTJS__*/", (DASH / "vendor" / "chart.umd.min.js").read_text(encoding="utf-8"))
            .replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False, separators=(",", ":"))))
    page = DASH / "slides.html"
    page.write_text(html, encoding="utf-8")
    out_dir = ROOT / "livrables"
    out_dir.mkdir(exist_ok=True)
    pdf = out_dir / "Presentation_Produits_Frais.pdf"
    chrome = next((c for c in CHROME if shutil.which(c) or __import__("os").path.exists(c)), None)
    if chrome is None:
        print("Chrome introuvable : ouvrez", page, "et imprimez en PDF (960x540 px, marges nulles).")
        return
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=5000",
                    f"--print-to-pdf={pdf}", page.as_uri()], check=True, capture_output=True)
    print("présentation écrite :", pdf)
    export_dashboard_pdf(chrome, out_dir / "Dashboard_Produits_Frais.pdf")


def export_dashboard_pdf(chrome: str, pdf) -> None:
    """PDF du dashboard pour les envois par mail : une capture fidèle par page (Synthèse, Pertes & remises,
    Instructions), assemblées en un PDF."""
    import tempfile
    from pathlib import Path

    import pymupdf

    base = (DASH / "dashboard.html").read_text(encoding="utf-8")
    doc = pymupdf.open()
    jpgs = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(3):
            page = Path(td) / f"p{i}.html"
            page.write_text(base.replace("fillItems();render();",
                            f"fillItems();document.querySelectorAll('nav button')[{i}].click();"), encoding="utf-8")
            png = Path(td) / f"p{i}.png"
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1300,930",
                            "--virtual-time-budget=4000", f"--screenshot={png}", page.as_uri()], check=True, capture_output=True)
            img = pymupdf.open(png)
            rect = img[0].rect
            jpg = img[0].get_pixmap(dpi=72).tobytes("jpg", jpg_quality=88)
            jpgs.append(jpg)
            doc.new_page(width=rect.width * 0.6, height=rect.height * 0.6).insert_image(
                pymupdf.Rect(0, 0, rect.width * 0.6, rect.height * 0.6), stream=jpg)
    doc.save(pdf, deflate=True, garbage=3)
    print("dashboard PDF écrit :", pdf)
    _inject_static_fallback(jpgs)


def _inject_static_fallback(jpgs: list[bytes]) -> None:
    """Ajoute des captures statiques, affichées uniquement si JavaScript est bloqué (aperçu de messagerie,
    visionneuse sécurisée…). Quand le script tourne, elles sont masquées immédiatement."""
    import base64

    imgs = "".join(f'<img alt="Aperçu du dashboard" style="max-width:100%;display:block;margin:0 auto 14px;border:1px solid #d9dee5" '
                   f'src="data:image/jpeg;base64,{base64.b64encode(j).decode()}">' for j in jpgs)
    block = ('<div id="nojs" style="padding:12px;font-family:Arial,sans-serif"><p style="text-align:center;color:#6b7280">'
             "Aperçu statique : ouvrez ce fichier dans Chrome, Safari ou Firefox pour utiliser les filtres.</p>"
             f"{imgs}</div><script>document.getElementById('nojs').style.display='none'</script>")
    path = DASH / "dashboard.html"
    html = path.read_text(encoding="utf-8")
    if 'id="nojs"' not in html:
        path.write_text(html.replace('<div class="wrap">', block + '\n<div class="wrap">', 1), encoding="utf-8")


if __name__ == "__main__":
    main()
