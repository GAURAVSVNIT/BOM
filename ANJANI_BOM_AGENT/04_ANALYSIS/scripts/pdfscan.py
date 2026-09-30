# -*- coding: utf-8 -*-
import os, warnings
warnings.filterwarnings("ignore")
import fitz

ROOT = r"C:\Users\Nikhil1616\Desktop\BOM\All_Things"
targets = ["SPEC JIEXP-051.pdf", "COMPONENT C23 SPEC (1).PDF", "Asahi Modi Quotation.pdf",
           "img20250402_13121346.pdf", "FIBC JUMBO BAG (1) (1).pdf",
           r"Scanned Documents\Image_20250414_0001.pdf"]
for t in targets:
    p = os.path.join(ROOT, t)
    if not os.path.exists(p):
        print(f"!! missing {t}"); continue
    try:
        doc = fitz.open(p)
        txt = doc[0].get_text().strip()
        print("\n" + "="*95)
        print(f"### {t}   pages={len(doc)}  chars_on_p1={len(txt)}")
        print("="*95)
        print(txt[:1600] if txt else "  [NO TEXT LAYER — scanned image, needs OCR]")
        doc.close()
    except Exception as e:
        print(f"!! {t}: {e}")
