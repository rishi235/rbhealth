"""Build prices.json for the pharmacy websites from the Google Sheet.

Source: the Sheet's "Broadcast" tab (Category, Product, Retail), published to
the web as CSV. Only these three columns are ever read, so costs and margins
can never reach the websites.

Usage:
  python build_prices.py <csv-url-or-file> [prices.json]

Safety: if the source looks wrong (download failed, columns renamed, too few
rows) the script exits with an error and leaves the existing prices.json in
place, so the websites keep showing the last good prices.
"""
import csv
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

MIN_ITEMS = 40

# Rows with an empty Category in the Sheet get one from their product name.
CATEGORY_GUESSES = [
    (r"sildenafil|vardenafil|tadalafil", "Erectile Dysfunction"),
    (r"otomize|ear ", "Ear Infection"),
]


def read_source(src):
    if src.startswith("http"):
        req = urllib.request.Request(src, headers={"User-Agent": "rbhealth-prices"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8-sig")
    with open(src, encoding="utf-8-sig") as f:
        return f.read()


def clean_price(value):
    value = (value or "").replace(" ", " ").strip()
    m = re.search(r"\d+(?:[.,]\d+)?", value.replace(",", ""))
    if not m:
        return None
    return "£{:.2f}".format(float(m.group()))


def clean_text(value):
    return re.sub(r"\s+", " ", (value or "").replace("​", "")).strip()


def build(text):
    rows = list(csv.reader(io.StringIO(text)))
    header = [clean_text(h).lower() for h in rows[0]]
    try:
        i_cat, i_prod, i_price = header.index("category"), header.index("product"), header.index("retail")
    except ValueError:
        sys.exit("Source is missing a Category, Product or Retail column: %s" % rows[0][:6])
    # Accept the full Prices tab too: only rows marked Broadcast = Yes.
    i_bc = header.index("broadcast") if "broadcast" in header else None

    categories = {}
    for r in rows[1:]:
        if len(r) <= max(i_cat, i_prod, i_price):
            continue
        if i_bc is not None and clean_text(r[i_bc]).lower() != "yes":
            continue
        product, price = clean_text(r[i_prod]), clean_price(r[i_price])
        if not product or not price:
            continue
        category = clean_text(r[i_cat])
        if not category:
            category = next((c for pat, c in CATEGORY_GUESSES if re.search(pat, product, re.I)), "Other Treatments")
        categories.setdefault(category, []).append({"productName": product, "retail": price})

    count = sum(len(v) for v in categories.values())
    if count < MIN_ITEMS:
        sys.exit("Only %d priced items found (expected at least %d) - not updating." % (count, MIN_ITEMS))
    return {
        "success": True,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": count,
        "categorized": categories,
    }


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "prices.json"
    data = build(read_source(src))
    try:
        with open(out, encoding="utf-8") as f:
            old = json.load(f)
        if old.get("categorized") == data["categorized"]:
            print("No price changes.")
            return
    except (OSError, ValueError):
        pass
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("Wrote %d items in %d categories to %s" % (data["count"], len(data["categorized"]), out))


if __name__ == "__main__":
    main()
