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


if __name__ == "__main__":
    main()
