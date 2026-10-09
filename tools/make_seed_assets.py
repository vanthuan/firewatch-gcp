# /// script
# requires-python = ">=3.11"
# dependencies = ["reportlab>=4.2", "pillow>=10.4"]
# ///
"""Generate the files under data/seed/ (deterministic; commit the output).

    uv run tools/make_seed_assets.py

Writes:
  data/seed/catalog.csv          products (SKU, line, price per 2.5 L, coverage, colour)
  data/seed/journalists.csv      synthetic journalists (fake names, example.com emails)
  data/seed/articles.csv         two recent article titles per journalist
  data/seed/swatches/<sku>.png   one colour swatch per product
  data/seed/briefs/*.pdf         five launch briefs with a spec table and swatch
"""

import csv
import random
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SEED = Path(__file__).resolve().parents[1] / "data" / "seed"

# sku, name, line, price per 2.5 L, coverage m2/L, finish, colour name, hex, use
PRODUCTS = [
    ("ECO-MAT-SAGE", "EcoGreen Interior Matte - Sage", "EcoGreen", 54.99, 12.0, "matte", "Sage", "#9CAF88", "interior"),
    ("ECO-MAT-LINEN", "EcoGreen Interior Matte - Linen", "EcoGreen", 54.99, 12.0, "matte", "Linen", "#EDE3D2", "interior"),
    ("ECO-MAT-CHAR", "EcoGreen Interior Matte - Charcoal", "EcoGreen", 54.99, 12.0, "matte", "Charcoal", "#3E4145", "interior"),
    ("DUR-SAT-HARB", "DuraCoat Exterior Satin - Harbor Blue", "DuraCoat", 69.99, 10.0, "satin", "Harbor Blue", "#2F5D7C", "exterior"),
    ("DUR-SAT-STONE", "DuraCoat Exterior Satin - Stone Grey", "DuraCoat", 69.99, 10.0, "satin", "Stone Grey", "#8A8D8F", "exterior"),
    ("PUR-CEIL-WHT", "PureMatte Ceiling White", "PureMatte", 39.99, 14.0, "flat", "Brilliant White", "#FAFAF7", "interior"),
    ("KID-EGG-SKY", "KidsSafe Washable Eggshell - Sky", "KidsSafe", 49.99, 11.0, "eggshell", "Sky", "#A7C7E7", "interior"),
    ("KID-EGG-BUTTER", "KidsSafe Washable Eggshell - Butter", "KidsSafe", 49.99, 11.0, "eggshell", "Butter", "#F6E3A1", "interior"),
    ("PRM-PRO-WHT", "Cymbal Primer Pro", "Primer", 34.99, 9.0, "flat", "White", "#FFFFFF", "interior/exterior"),
    ("CLS-EMU-MAG", "Classic Emulsion - Magnolia", "Classic", 29.99, 13.0, "matte", "Magnolia", "#F3E9D8", "interior"),
    ("CLS-GLS-WHT", "Classic Gloss - White", "Classic", 32.99, 12.0, "gloss", "White", "#FDFDFD", "interior/exterior"),
    ("FLR-SAT-SLATE", "FloorGuard Satin - Slate", "FloorGuard", 59.99, 8.0, "satin", "Slate", "#5A6068", "interior"),
]

# One launch brief per new product line. Prices and coverage match PRODUCTS exactly,
# so extraction evals (Step 2.8) can compare against the catalog.
BRIEFS = [
    {
        "file": "01-ecogreen-interior-matte.pdf",
        "sku": "ECO-MAT-SAGE",
        "title": "Launch brief: EcoGreen Interior Matte",
        "promo": "20% off until Jun 30",
        "launch": "2027-03-01",
        "audience": "Eco-conscious homeowners redecorating living spaces",
        "features": ["Low-VOC formula (under 5 g/L)", "Made with 30% plant-based binders", "One-coat coverage over light colours", "Washable matte finish"],
    },
    {
        "file": "02-duracoat-exterior-satin.pdf",
        "sku": "DUR-SAT-HARB",
        "title": "Launch brief: DuraCoat Exterior Satin",
        "promo": "Buy 3 cans, get the 4th free",
        "launch": "2027-04-15",
        "audience": "DIY homeowners in coastal and high-humidity regions",
        "features": ["Salt-spray and UV resistant", "Rain-proof in 1 hour", "Mildew-resistant film", "15-year exterior warranty"],
    },
    {
        "file": "03-purematte-ceiling-white.pdf",
        "sku": "PUR-CEIL-WHT",
        "title": "Launch brief: PureMatte Ceiling White",
        "promo": None,
        "launch": "2027-02-10",
        "audience": "Professional decorators and contractors",
        "features": ["Anti-splatter formula for overhead work", "Ultra-flat finish hides imperfections", "Turns from pink to white when dry", "Touch dry in 30 minutes"],
    },
    {
        "file": "04-kidssafe-washable-eggshell.pdf",
        "sku": "KID-EGG-SKY",
        "title": "Launch brief: KidsSafe Washable Eggshell",
        "promo": "Free roller kit with every 2.5 L can in March",
        "launch": "2027-03-20",
        "audience": "Parents decorating nurseries and children's rooms",
        "features": ["Scrubbable: survives 10,000 scrub cycles", "Toy-safe certified (EN 71-3)", "Stain-release crayon and marker resistance", "Near-zero odour"],
    },
    {
        "file": "05-cymbal-primer-pro.pdf",
        "sku": "PRM-PRO-WHT",
        "title": "Launch brief: Cymbal Primer Pro",
        "promo": "15% off for trade accounts until May 31",
        "launch": "2027-01-25",
        "audience": "Renovators preparing damaged or stained surfaces",
        "features": ["Blocks water, smoke and tannin stains", "Bonds to tile, glass and glossy surfaces", "Interior and exterior use", "Recoat in 2 hours"],
    },
]

FIRST = ["Ava", "Liam", "Maya", "Noah", "Zoe", "Ethan", "Priya", "Lucas", "Hana", "Omar",
         "Chloe", "Diego", "Nina", "Samuel", "Leila", "Marcus", "Ines", "Tomas", "Grace", "Kofi"]
LAST = ["Harper", "Nguyen", "Okafor", "Silva", "Brennan", "Kowalski", "Patel", "Moreau",
        "Tanaka", "Haddad", "Lindqvist", "Reyes", "Fischer", "Mensah", "O'Neill", "Castillo"]
OUTLETS = ["Home & Hearth Weekly", "The Renovation Report", "Green Living Daily", "Trade Paint Journal",
           "Coastal Homes Magazine", "Design Desk", "DIY Nation", "Retail Pulse"]
REGIONS = ["US-Northeast", "US-South", "US-Midwest", "US-West", "UK", "Canada"]
BEATS = ["home-improvement", "sustainability", "interior-design", "diy", "retail",
         "construction-trade", "consumer-products", "real-estate"]
TITLE_TEMPLATES = {
    "home-improvement": ["Five weekend upgrades that add value", "What renovators are buying this spring"],
    "sustainability": ["Low-VOC paints move into the mainstream", "Can a paint can be circular?"],
    "interior-design": ["Earthy greens are this year's neutral", "Designers pick their favourite matte finishes"],
    "diy": ["How to paint a ceiling without the mess", "Primer: the step DIYers skip"],
    "retail": ["Home-improvement sales cool after a record year", "Why paint brands are betting on trade accounts"],
    "construction-trade": ["Contractors face coatings shortages", "Faster-drying coatings cut job times"],
    "consumer-products": ["Washable paints put to the crayon test", "The rise of odour-free household products"],
    "real-estate": ["Paint colours that help homes sell", "Coastal homes and the cost of weathering"],
}


def write_catalog() -> None:
    with open(SEED / "catalog.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sku", "name", "line", "price_usd", "container_l", "coverage_m2_l", "finish", "colour", "hex", "use"])
        for sku, name, line, price, cov, finish, colour, hexv, use in PRODUCTS:
            w.writerow([sku, name, line, f"{price:.2f}", "2.5", f"{cov:.1f}", finish, colour, hexv, use])


def write_swatches() -> None:
    out = SEED / "swatches"
    out.mkdir(parents=True, exist_ok=True)
    for sku, *_, hexv, _use in PRODUCTS:
        Image.new("RGB", (256, 256), hexv).save(out / f"{sku}.png", optimize=True)


def write_journalists(n: int = 40) -> None:
    rng = random.Random(42)
    seen: set[str] = set()
    rows, articles = [], []
    while len(rows) < n:
        first, last = rng.choice(FIRST), rng.choice(LAST)
        email = f"{first}.{last}".lower().replace("'", "") + "@example.com"
        if email in seen:
            continue
        seen.add(email)
        outlet, region = rng.choice(OUTLETS), rng.choice(REGIONS)
        beats = sorted(rng.sample(BEATS, k=rng.choice([1, 2, 3])))
        bio = f"{first} {last} covers {', '.join(b.replace('-', ' ') for b in beats)} for {outlet}, based in {region}."
        opted_out = len(rows) % 8 == 7  # every 8th journalist has opted out
        rows.append([f"{first} {last}", email, outlet, region, ";".join(beats), bio, str(opted_out).lower()])
        for i, title in enumerate(TITLE_TEMPLATES[beats[0]]):
            slug = title.lower().replace(" ", "-").replace(":", "").replace("?", "").replace("'", "")
            day = rng.randint(1, 28)
            articles.append([email, title, f"https://news.example.com/{slug}-{len(rows)}-{i}", f"2026-0{rng.randint(6, 9)}-{day:02d}"])

    with open(SEED / "journalists.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["full_name", "email", "outlet", "region", "beats", "bio", "opted_out"])
        w.writerows(rows)
    with open(SEED / "articles.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["journalist_email", "title", "url", "published_at"])
        w.writerows(articles)


def write_briefs() -> None:
    out = SEED / "briefs"
    out.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    by_sku = {p[0]: p for p in PRODUCTS}
    for b in BRIEFS:
        sku, name, line, price, cov, finish, colour, hexv, use = by_sku[b["sku"]]
        doc = SimpleDocTemplate(str(out / b["file"]), pagesize=A4, title=b["title"],
                                author="Cymbal Marketing", invariant=True)
        spec = Table(
            [["Spec", "Value"],
             ["SKU", sku], ["Product line", line], ["Price (2.5 L)", f"${price:.2f}"],
             ["Coverage", f"{cov:.1f} m2 per litre"], ["Finish", finish], ["Launch colour", colour],
             ["Use", use], ["Launch date", b["launch"]]],
            colWidths=[5 * cm, 9 * cm],
        )
        spec.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E6B52")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        story = [
            Paragraph(b["title"], styles["Title"]),
            Paragraph("Cymbal Paints - Marketing launch brief (sample data)", styles["Italic"]),
            Spacer(1, 12),
            Paragraph(f"<b>Product:</b> {name}", styles["Normal"]),
            Paragraph(f"<b>Audience:</b> {b['audience']}", styles["Normal"]),
            Paragraph(f"<b>Promotion:</b> {b['promo'] or 'None at launch'}", styles["Normal"]),
            Spacer(1, 12),
            Paragraph("Key features", styles["Heading2"]),
            *[Paragraph(f"- {feat}", styles["Normal"]) for feat in b["features"]],
            Spacer(1, 12),
            Paragraph("Specifications", styles["Heading2"]),
            spec,
            Spacer(1, 12),
            Paragraph(f"Launch colour swatch: {colour}", styles["Heading2"]),
            RLImage(str(SEED / "swatches" / f"{sku}.png"), width=4 * cm, height=4 * cm),
        ]
        doc.build(story)


if __name__ == "__main__":
    SEED.mkdir(parents=True, exist_ok=True)
    write_catalog()
    write_swatches()
    write_journalists()
    write_briefs()
    print(f"wrote seed files to {SEED}")
