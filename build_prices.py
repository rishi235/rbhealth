"""Build prices.json for the pharmacy websites from the Google Sheet.

Sources (both published to the web as CSV):
  - "Broadcast" tab: Category, Product, Retail. Only these three columns are
    ever read, so costs and margins can never reach the websites.
  - "Website Stores" tab: one row per website with tick boxes for which
    services that store offers. Unticked services are hidden on that site.

Usage:
  python build_prices.py <prices-csv-url-or-file> [prices.json] [stores-csv-url-or-file]

Safety: if the price source looks wrong (download failed, columns renamed, too
few rows) the script exits with an error and leaves the existing prices.json in
place, so the websites keep showing the last good prices. If only the stores
source fails, the previous store settings are kept.
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

# Service groups = tick-box columns on the "Website Stores" tab (till depts in brackets).
GROUP_COLUMNS = {
    "bloods": "blood tests",      # CLB
    "travel": "travel",           # CLI
    "weightloss": "weight loss",  # CLW
    "other": "other treatments",  # everything else
}


def group_for(category):
    c = category.lower()
    if "blood" in c:
        return "bloods"
    if "travel" in c:
        return "travel"
    if "weight" in c:
        return "weightloss"
    return "other"


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


def site_key(value):
    """'https://www.Hirshmanspharmacy.co.uk/x' -> 'hirshmanspharmacy.co.uk'"""
    v = clean_text(value).lower()
    v = re.sub(r"^https?://", "", v).split("/")[0]
    return re.sub(r"^www\.", "", v)


def build_prices(text):
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
    return categories, count


def build_stores(text):
    rows = list(csv.reader(io.StringIO(text)))
    header = [clean_text(h).lower() for h in rows[0]]
    i_site = next(i for i, h in enumerate(header) if h.startswith("website"))
    cols = {g: next(i for i, h in enumerate(header) if h.startswith(name)) for g, name in GROUP_COLUMNS.items()}
    stores = {}
    for r in rows[1:]:
        if len(r) <= i_site or not site_key(r[i_site]):
            continue
        ticked = [g for g, i in cols.items() if i < len(r) and clean_text(r[i]).lower() in ("true", "yes", "y", "1", "x", "✓")]
        stores[site_key(r[i_site])] = ticked
    if not stores:
        raise ValueError("no stores found")
    return stores


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "prices.json"
    stores_src = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        with open(out, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = {}

    categories, count = build_prices(read_source(src))
    stores = old.get("stores", {})
    if stores_src:
        try:
            stores = build_stores(read_source(stores_src))
        except Exception as e:  # keep previous store settings rather than failing
            print("Could not read stores (%s) - keeping previous settings." % e)

    data = {
        "success": True,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": count,
        "categorized": categories,
        "groups": {c: group_for(c) for c in categories},
        "stores": stores,
    }
    if all(old.get(k) == data[k] for k in ("categorized", "groups", "stores")):
        print("No changes.")
        return
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("Wrote %d items in %d categories, %d stores to %s" % (count, len(categories), len(stores), out))


if __name__ == "__main__":
    main()
