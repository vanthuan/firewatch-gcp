# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "google-auth[requests]>=2.35",
#   "google-cloud-storage>=2.18",
#   "psycopg[binary]>=3.2",
# ]
# ///
"""Load data/seed/ into a dev environment. Safe to re-run: every write is an upsert.

    make seed                      # or: uv run tools/seed.py
    uv run tools/seed.py --only db # one part: gcs, db, search

What it loads:
  gcs     briefs  -> gs://{project}-briefs/{org}/seed-NN/<file>.pdf
          swatches-> gs://{project}-assets/swatches/<sku>.png
  db      products, journalists, articles -> DATABASE_URL (local pgvector by default;
          AlloyDB is private-IP only, so seed it from a Cloud Run job in the VPC, Step 1.7)
  search  catalog JSONL -> gs://{project}-artifacts/catalog/products.jsonl, imported into the
          Vertex AI Search `catalog` datastore; the briefs are imported into `kb` (both from Step 2.3)

Environment: GOOGLE_CLOUD_PROJECT (else ADC's project), DATABASE_URL, SEED_ORG_ID,
CATALOG_DATASTORE_ID, SEARCH_LOCATION.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import google.auth
import psycopg
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
SCHEMA = Path(__file__).resolve().parent / "sql" / "schema.sql"

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:dev@localhost:5433/launchpad")
ORG_ID = os.environ.get("SEED_ORG_ID", "demo-org")
DATASTORE_ID = os.environ.get("CATALOG_DATASTORE_ID", "catalog")
KB_DATASTORE_ID = os.environ.get("KB_DATASTORE_ID", "kb")
SEARCH_LOCATION = os.environ.get("SEARCH_LOCATION", "global")


def read_csv(name: str) -> list[dict[str, str]]:
    with open(SEED / name, newline="") as f:
        return list(csv.DictReader(f))


def resolve_project() -> str:
    credentials, adc_project = google.auth.default()
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or adc_project
    if not project:
        sys.exit("Set GOOGLE_CLOUD_PROJECT (no project in Application Default Credentials).")
    return project


# ---------- GCS: briefs and swatches ----------
def seed_gcs(project: str) -> None:
    client = storage.Client(project=project)
    briefs = client.bucket(f"{project}-briefs")
    assets = client.bucket(f"{project}-assets")

    for n, pdf in enumerate(sorted((SEED / "briefs").glob("*.pdf")), start=1):
        blob = briefs.blob(f"{ORG_ID}/seed-{n:02d}/{pdf.name}")
        blob.metadata = {"source": "seed", "campaign_id": f"seed-{n:02d}"}
        blob.upload_from_filename(pdf, content_type="application/pdf")
        print(f"  brief    gs://{briefs.name}/{blob.name}")

    swatches = sorted((SEED / "swatches").glob("*.png"))
    for png in swatches:
        assets.blob(f"swatches/{png.name}").upload_from_filename(png, content_type="image/png")
    print(f"  swatches {len(swatches)} -> gs://{assets.name}/swatches/")


# ---------- Postgres / AlloyDB: products, journalists, articles ----------
def product_rows(project: str) -> list[dict]:
    return [
        {
            "sku": p["sku"], "name": p["name"], "line": p["line"],
            "price_usd": p["price_usd"], "container_l": p["container_l"],
            "coverage_m2_l": p["coverage_m2_l"],
            "image_uri": f"gs://{project}-assets/swatches/{p['sku']}.png",
            "attributes": {"finish": p["finish"], "colour": p["colour"], "hex": p["hex"], "use": p["use"]},
        }
        for p in read_csv("catalog.csv")
    ]


def seed_db(project: str) -> None:
    products = product_rows(project)
    journalists = read_csv("journalists.csv")
    articles = read_csv("articles.csv")

    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(SCHEMA.read_text())

        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO products (sku, name, line, price_usd, container_l, coverage_m2_l, image_uri, attributes)
                   VALUES (%(sku)s, %(name)s, %(line)s, %(price_usd)s, %(container_l)s, %(coverage_m2_l)s,
                           %(image_uri)s, %(attributes)s)
                   ON CONFLICT (sku) DO UPDATE SET
                     name = EXCLUDED.name, line = EXCLUDED.line, price_usd = EXCLUDED.price_usd,
                     container_l = EXCLUDED.container_l, coverage_m2_l = EXCLUDED.coverage_m2_l,
                     image_uri = EXCLUDED.image_uri, attributes = EXCLUDED.attributes""",
                [{**p, "attributes": Jsonb(p["attributes"])} for p in products],
            )

            # Upsert on email and keep opted_out as given (real imports never clear an opt-out).
            cur.executemany(
                """INSERT INTO journalists (full_name, email, outlet, region, beats, bio, opted_out)
                   VALUES (%(full_name)s, %(email)s, %(outlet)s, %(region)s, %(beats)s, %(bio)s, %(opted_out)s)
                   ON CONFLICT (email) DO UPDATE SET
                     full_name = EXCLUDED.full_name, outlet = EXCLUDED.outlet, region = EXCLUDED.region,
                     beats = EXCLUDED.beats, bio = EXCLUDED.bio,
                     opted_out = journalists.opted_out OR EXCLUDED.opted_out, updated_at = now()""",
                [{**j, "beats": j["beats"].split(";"), "opted_out": j["opted_out"] == "true"} for j in journalists],
            )

            # Articles have no natural key in the Step 4.1 schema: replace the seeded journalists' set.
            emails = [j["email"] for j in journalists]
            cur.execute("SELECT email, id FROM journalists WHERE email = ANY(%s)", (emails,))
            ids = dict(cur.fetchall())
            cur.execute("DELETE FROM articles WHERE journalist_id = ANY(%s)", (list(ids.values()),))
            cur.executemany(
                "INSERT INTO articles (journalist_id, title, url, published_at) VALUES (%s, %s, %s, %s)",
                [(ids[a["journalist_email"]], a["title"], a["url"], a["published_at"]) for a in articles],
            )

    target = DATABASE_URL.rsplit("@", 1)[-1]
    print(f"  db       {len(products)} products, {len(journalists)} journalists, {len(articles)} articles -> {target}")


# ---------- Vertex AI Search: catalog ----------
def seed_search(project: str) -> None:
    lines = []
    for p in product_rows(project):
        attributes = p.pop("attributes")
        struct = {**p, **attributes}
        struct["price_usd"] = float(struct["price_usd"])
        struct["container_l"] = float(struct["container_l"])
        struct["coverage_m2_l"] = float(struct["coverage_m2_l"])
        lines.append(json.dumps({"id": p["sku"], "structData": struct}))

    uri = f"gs://{project}-artifacts/catalog/products.jsonl"
    bucket, name = uri[5:].split("/", 1)
    storage.Client(project=project).bucket(bucket).blob(name).upload_from_string(
        "\n".join(lines) + "\n", content_type="application/jsonl"
    )
    print(f"  catalog  {len(lines)} products -> {uri}")

    # The catalog is the whole product list, so FULL replaces it. The kb also receives documents
    # from the ingest worker (Step 2.5), so briefs are added INCREMENTAL. Content imports derive
    # document IDs from the GCS URI, so re-seeding overwrites instead of duplicating.
    briefs = [
        f"gs://{project}-briefs/{ORG_ID}/seed-{n:02d}/{pdf.name}"
        for n, pdf in enumerate(sorted((SEED / "briefs").glob("*.pdf")), start=1)
    ]
    start_import(project, DATASTORE_ID, {"inputUris": [uri], "dataSchema": "document"}, "FULL")
    start_import(project, KB_DATASTORE_ID, {"inputUris": briefs, "dataSchema": "content"}, "INCREMENTAL")


def start_import(project: str, datastore_id: str, gcs_source: dict, mode: str) -> None:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(credentials)
    host = "discoveryengine.googleapis.com" if SEARCH_LOCATION == "global" else f"{SEARCH_LOCATION}-discoveryengine.googleapis.com"
    store = f"projects/{project}/locations/{SEARCH_LOCATION}/collections/default_collection/dataStores/{datastore_id}"
    headers = {"x-goog-user-project": project}

    if session.get(f"https://{host}/v1/{store}", headers=headers).status_code == 404:
        print(f"  search   skipped {datastore_id}: datastore not found (Step 2.3), re-run with --only search")
        return

    resp = session.post(
        f"https://{host}/v1/{store}/branches/default_branch/documents:import",
        headers=headers,
        json={"gcsSource": gcs_source, "reconciliationMode": mode},
    )
    resp.raise_for_status()
    print(f"  search   {datastore_id}: import started ({len(gcs_source['inputUris'])} source(s)), {resp.json()['name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=["gcs", "db", "search"], action="append",
                        help="run only these parts (repeatable); default: all")
    parts = parser.parse_args().only or ["gcs", "db", "search"]

    project = resolve_project()
    print(f"Seeding project {project} (org {ORG_ID})")
    if "gcs" in parts:
        seed_gcs(project)
    if "db" in parts:
        seed_db(project)
    if "search" in parts:
        seed_search(project)
    print("Done.")


if __name__ == "__main__":
    main()
