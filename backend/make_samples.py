"""Generate the deterministic demo invoices described in spec §11.

Run once (locally or in the container) to populate sample_data/invoices/ with:
  1. clean.pdf                 - reconciles, high confidence (happy path)
  2. photo_scan.jpg            - skewed/noisy valid invoice (triggers escalation)
  3. wrong_total.pdf           - validation catches a bad total
  4. changed_bank.pdf          - fraud catches a changed vendor bank account
  5. near_duplicate.pdf        - semantic dedup catches an altered invoice number
  6. no_po.pdf                 - STRETCH: three-way match finds no matching PO

The vendor/number/bank values here line up with seed.py so checks 4 and 5 fire.
"""

from __future__ import annotations

import os

import fitz  # PyMuPDF
from PIL import Image

OUT_DIR = os.path.join(os.path.dirname(__file__), "sample_data", "invoices")
os.makedirs(OUT_DIR, exist_ok=True)


def _draw_invoice(
    path: str,
    vendor: str,
    number: str,
    date: str,
    bank: str,
    items: list[tuple[str, int, float, float]],
    subtotal: float,
    tax: float,
    total: float,
    currency: str = "USD",
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 @ 72dpi
    x = 60
    y = 60

    def line(text, size=11, dy=18, bold=False, color=(0, 0, 0)):
        nonlocal y
        font = "helv" if not bold else "hebo"
        page.insert_text((x, y), text, fontsize=size, fontname=font, color=color)
        y += dy

    line("INVOICE", size=24, dy=34, bold=True)
    line(vendor, size=14, dy=22, bold=True)
    line("123 Commerce Ave, Metropolis", dy=16)
    line("accounts@vendor.example", dy=28)

    line(f"Invoice Number: {number}", bold=True)
    line(f"Invoice Date: {date}")
    line(f"Currency: {currency}")
    line(f"Bank Account: {bank}", dy=28)

    # Table header
    line("Description            Qty     Unit Price      Amount", bold=True, dy=20)
    for desc, qty, price, amount in items:
        row = f"{desc:<22}{qty:<8}{price:<15.2f}{amount:.2f}"
        line(row, dy=18)

    y += 10
    line(f"Subtotal: {subtotal:.2f}", dy=18)
    line(f"Tax: {tax:.2f}", dy=18)
    line(f"Total: {total:.2f}", size=13, bold=True, dy=18)

    doc.save(path)
    doc.close()
    print(f"wrote {path}")


def _draw_resume(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    x, y = 55, 60

    def line(text, size=11, dy=16, bold=False, color=(0, 0, 0)):
        nonlocal y
        page.insert_text((x, y), text, fontsize=size, fontname="hebo" if bold else "helv", color=color)
        y += dy

    line("Priya Sharma", size=22, dy=26, bold=True)
    line("Senior Data Scientist", size=13, dy=18, color=(0.3, 0.3, 0.35))
    line("priya.sharma@email.com  ·  +1 415 555 0198  ·  San Francisco, CA", dy=24)

    line("SUMMARY", size=11, dy=16, bold=True)
    line("Data scientist with 7 years building machine learning systems in Python.", dy=14)
    line("Specializes in NLP, deep learning, and deploying models to production.", dy=24)

    line("SKILLS", size=11, dy=16, bold=True)
    line("Python, PyTorch, TensorFlow, scikit-learn, SQL, NLP, LLMs, AWS, Docker, MLOps", dy=24)

    line("EXPERIENCE", size=11, dy=16, bold=True)
    line("Senior Data Scientist — Orion Analytics", dy=14, bold=True)
    line("2021 - Present  ·  Led an NLP platform serving 20M requests/day.", dy=18)
    line("Data Scientist — Nimbus AI", dy=14, bold=True)
    line("2018 - 2021  ·  Built recommendation and fraud-detection models.", dy=24)

    line("EDUCATION", size=11, dy=16, bold=True)
    line("M.S. Computer Science, Stanford University — 2018", dy=14)

    doc.save(path)
    doc.close()
    print(f"wrote {path}")


def _draw_receipt(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=380, height=560)
    x, y = 40, 50

    def line(text, size=11, dy=16, bold=False):
        nonlocal y
        page.insert_text((x, y), text, fontsize=size, fontname="hebo" if bold else "helv")
        y += dy

    line("COSMIC COFFEE ROASTERS", size=14, dy=20, bold=True)
    line("221 Nebula Street, Portland OR", dy=14)
    line("Date: 2026-08-12   14:32", dy=14)
    line("Payment: Visor Card ****4417", dy=24)
    line("-" * 34, dy=16)
    line("Cappuccino              4.50", dy=14)
    line("Blueberry muffin        3.25", dy=14)
    line("Cold brew (large)       5.00", dy=16)
    line("-" * 34, dy=16)
    line("Subtotal               12.75", dy=14)
    line("Tax                     1.08", dy=14)
    line("TOTAL                  13.83", dy=16, bold=True)
    line("-" * 34, dy=18)
    line("Thank you! See you again.", dy=14)

    doc.save(path)
    doc.close()
    print(f"wrote {path}")


def main() -> None:
    # 1. Clean, reconciles.
    _draw_invoice(
        os.path.join(OUT_DIR, "clean.pdf"),
        vendor="Nebula Office Supplies",
        number="INV-2026-001",
        date="2026-06-15",
        bank="ACCT-1122334455",
        items=[
            ("Ergonomic chair", 4, 180.00, 720.00),
            ("Standing desk", 1, 360.00, 360.00),
        ],
        subtotal=1080.00,
        tax=86.40,
        total=1166.40,
    )

    # 3. Wrong total (subtotal+tax != total, and lines != subtotal).
    _draw_invoice(
        os.path.join(OUT_DIR, "wrong_total.pdf"),
        vendor="Apex Hardware Co",
        number="INV-2026-042",
        date="2026-07-02",
        bank="ACCT-9090909090",
        items=[
            ("Power drill", 2, 120.00, 240.00),
            ("Drill bits set", 3, 25.00, 75.00),
        ],
        subtotal=315.00,
        tax=25.20,
        total=999.99,  # deliberately wrong
    )

    # 4. Changed bank account. Vendor 'Meridian Logistics' is seeded in the ledger
    #    with a DIFFERENT bank account, so the fraud layer flags the change.
    _draw_invoice(
        os.path.join(OUT_DIR, "changed_bank.pdf"),
        vendor="Meridian Logistics",
        number="INV-2026-500",
        date="2026-07-20",
        bank="ACCT-6666666666",  # differs from seeded ACCT-4444333322
        items=[
            ("Freight haul - Route A", 1, 1500.00, 1500.00),
        ],
        subtotal=1500.00,
        tax=120.00,
        total=1620.00,
    )

    # 5. Near-duplicate. Seed has 'Stellar Freight' INV-7788; this is INV-7789,
    #    everything else identical -> semantic dedup flags the altered number.
    _draw_invoice(
        os.path.join(OUT_DIR, "near_duplicate.pdf"),
        vendor="Stellar Freight",
        number="INV-7789",  # one digit off from the approved INV-7788
        date="2026-05-10",
        bank="ACCT-7777888899",
        items=[
            ("Ocean shipping container", 2, 950.00, 1900.00),
            ("Customs handling", 1, 150.00, 150.00),
        ],
        subtotal=2050.00,
        tax=164.00,
        total=2214.00,
    )

    # 6. STRETCH: no matching PO (vendor absent from pos.json).
    _draw_invoice(
        os.path.join(OUT_DIR, "no_po.pdf"),
        vendor="Ghost Vendor LLC",
        number="INV-2026-777",
        date="2026-08-01",
        bank="ACCT-0000111122",
        items=[
            ("Consulting services", 10, 150.00, 1500.00),
        ],
        subtotal=1500.00,
        tax=120.00,
        total=1620.00,
    )

    # 2. Phone photo / low-quality scan: render the clean invoice, then rotate +
    #    downscale + add noise so the default model reads it with low confidence
    #    and the router escalates.
    tmp = fitz.open()
    p = tmp.new_page(width=595, height=842)
    p.insert_text((60, 80), "INVOICE", fontsize=22, fontname="hebo")
    p.insert_text((60, 120), "Cosmic Catering Ltd", fontsize=14, fontname="hebo")
    p.insert_text((60, 150), "Invoice Number: INV-2026-909", fontsize=11)
    p.insert_text((60, 172), "Invoice Date: 2026-06-30", fontsize=11)
    p.insert_text((60, 194), "Currency: USD", fontsize=11)
    p.insert_text((60, 216), "Bank Account: ACCT-5151515151", fontsize=11)
    p.insert_text((60, 250), "Catering package     1     850.00     850.00", fontsize=11)
    p.insert_text((60, 280), "Subtotal: 850.00", fontsize=11)
    p.insert_text((60, 300), "Tax: 68.00", fontsize=11)
    p.insert_text((60, 320), "Total: 918.00", fontsize=13, fontname="hebo")
    pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_path = os.path.join(OUT_DIR, "photo_scan.jpg")
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    # Simulate a phone photo: rotate slightly, add a warm cast, downscale, JPEG.
    img = img.rotate(-4, expand=True, fillcolor=(245, 243, 235))
    img = img.resize((int(img.width * 0.6), int(img.height * 0.6)), Image.LANCZOS)
    img.save(img_path, "JPEG", quality=55)
    tmp.close()
    print(f"wrote {img_path}")

    # Other domains — prove the platform beyond invoices.
    _draw_resume(os.path.join(OUT_DIR, "resume.pdf"))
    _draw_receipt(os.path.join(OUT_DIR, "receipt.pdf"))


if __name__ == "__main__":
    main()
