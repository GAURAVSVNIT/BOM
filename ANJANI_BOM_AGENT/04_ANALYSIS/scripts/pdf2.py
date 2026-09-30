# -*- coding: utf-8 -*-
import os, re, warnings
warnings.filterwarnings("ignore")
import fitz
ROOT = r"C:\Users\Nikhil1616\Desktop\BOM"

p = os.path.join(ROOT, "Bulk Density List - National Bulk Bag.pdf")
doc = fitz.open(p)
print(f"### Bulk Density List — {len(doc)} pages")
t = "\n".join(doc[i].get_text() for i in range(min(3, len(doc))))
print(t[:2600])
doc.close()

print("\n\n" + "#"*90)
p = os.path.join(ROOT, "Buyer's Guide to UN Certified Bulk Bags.pdf")
doc = fitz.open(p)
print(f"### UN Certified Guide — {len(doc)} pages")
t = "\n".join(doc[i].get_text() for i in range(min(6, len(doc))))
t = re.sub(r"\n{3,}", "\n\n", t)
print(t[:3200])
doc.close()
