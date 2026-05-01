#!/usr/bin/env python3
"""
Build script/csv/items.csv rows using Google Places API (New).

Uses Nearby Search around each seed (Lat, Lng) from an input CSV, then optional
Text Search fallback. Writes real displayName, coordinates, and formattedAddress
from Google. Requires Places API (New) enabled for the key project.

Environment:
  GOOGLE_PLACES_API_KEY  (required)

Example:
  python script/fetch_items_from_places.py \\
    --input script/csv/items.csv \\
    --output script/csv/items.csv \\
    --in-place

  # Safer default writes to a new file:
  python script/fetch_items_from_places.py --input script/csv/items.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import time
from typing import Any

import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.types,places.rating,places.userRatingCount,places.businessStatus"
)


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }


def _places_post(
    session: requests.Session,
    url: str,
    api_key: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    r = session.post(url, headers=_headers(api_key), json=body, timeout=30)
    if r.status_code == 429:
        time.sleep(2.0)
        r = session.post(url, headers=_headers(api_key), json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def nearby_search(
    session: requests.Session,
    api_key: str,
    lat: float,
    lng: float,
    radius_m: float,
) -> list[dict[str, Any]]:
    bodies: list[dict[str, Any]] = [
        {
            "includedTypes": ["coffee_shop", "cafe"],
            "maxResultCount": 20,
            "rankPreference": "DISTANCE",
            "languageCode": "ja",
            "regionCode": "JP",
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m),
                }
            },
        },
        {
            "includedTypes": ["coffee_shop"],
            "maxResultCount": 20,
            "rankPreference": "DISTANCE",
            "languageCode": "ja",
            "regionCode": "JP",
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m),
                }
            },
        },
        {
            "includedTypes": ["cafe"],
            "maxResultCount": 20,
            "rankPreference": "DISTANCE",
            "languageCode": "ja",
            "regionCode": "JP",
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m),
                }
            },
        },
    ]
    last_err: Exception | None = None
    for body in bodies:
        try:
            data = _places_post(session, NEARBY_URL, api_key, body)
            return list(data.get("places") or [])
        except requests.HTTPError as e:
            last_err = e
            if e.response is not None and e.response.status_code == 400:
                continue
            raise
    if last_err:
        raise last_err
    return []


def text_search_fallback(
    session: requests.Session,
    api_key: str,
    lat: float,
    lng: float,
    address_hint: str,
    radius_m: float,
) -> list[dict[str, Any]]:
    q = f"cafe coffee shop {address_hint}".strip()
    body: dict[str, Any] = {
        "textQuery": q,
        "languageCode": "ja",
        "regionCode": "JP",
        "maxResultCount": 20,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": min(float(radius_m) * 3, 8000.0),
            }
        },
    }
    data = _places_post(session, TEXT_SEARCH_URL, api_key, body)
    return list(data.get("places") or [])


def pick_place(
    places: list[dict[str, Any]],
    used_ids: set[str],
) -> dict[str, Any] | None:
    for p in places:
        pid = p.get("id") or ""
        if pid and pid in used_ids:
            continue
        status = p.get("businessStatus")
        if status == "CLOSED_PERMANENTLY":
            continue
        name = (p.get("displayName") or {}).get("text") or ""
        if not name.strip():
            continue
        loc = p.get("location") or {}
        if loc.get("latitude") is None or loc.get("longitude") is None:
            continue
        return p
    return None


def place_to_csv_row(place: dict[str, Any], address_fallback: str) -> dict[str, str]:
    name = (place.get("displayName") or {}).get("text") or ""
    loc = place.get("location") or {}
    lat = loc.get("latitude")
    lng = loc.get("longitude")
    addr = (place.get("formattedAddress") or "").strip() or address_fallback
    types_ = place.get("types") or []
    parts = [t.replace("_", " ") for t in types_ if t][:6]
    rating = place.get("rating")
    if rating is not None:
        parts.append(f"Google rating {rating}")
    features = " | ".join(parts) if parts else "cafe"
    return {
        "Name": name.strip(),
        "Lat": f"{float(lat):.7f}",
        "Lng": f"{float(lng):.7f}",
        "Address": addr,
        "Features": features,
        "Agoda": "",
    }


def read_seed_rows(path: str) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"Empty CSV: {path}")
        fields = {h.strip().lower(): h for h in reader.fieldnames if h}
        lat_key = fields.get("lat") or fields.get("seedlat")
        lng_key = fields.get("lng") or fields.get("seedlng")
        addr_key = fields.get("address")
        if not lat_key or not lng_key:
            raise SystemExit(
                f"{path}: need Lat and Lng columns (or SeedLat/SeedLng)."
            )
        rows: list[dict[str, str]] = []
        for raw in reader:
            lat_s = (raw.get(lat_key) or "").strip()
            lng_s = (raw.get(lng_key) or "").strip()
            if not lat_s or not lng_s:
                continue
            addr = (raw.get(addr_key) or "Japan").strip() if addr_key else "Japan"
            rows.append(
                {
                    "_lat": lat_s,
                    "_lng": lng_s,
                    "_address": addr,
                    "_original": {k: raw.get(k, "") for k in reader.fieldnames},
                }
            )
        return rows


def write_items_csv(path: str, rows: list[dict[str, str]]) -> None:
    fieldnames = ["Name", "Lat", "Lng", "Address", "Features", "Agoda"]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fill items.csv from Google Places API (New) using seed Lat/Lng/Address.",
    )
    parser.add_argument(
        "--input",
        default=os.path.join(SCRIPT_DIR, "csv", "items.csv"),
        help="CSV with at least Lat, Lng, Address (Name is ignored).",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output CSV path (default: items_from_places.csv next to input).",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write results to --input (same path).",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="With --in-place, skip copying input to *.before_places.bak.csv first.",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=650.0,
        help="Nearby search radius in meters (default 650).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.12,
        help="Seconds between API calls (default 0.12).",
    )
    args = parser.parse_args()

    api_key = (os.environ.get("GOOGLE_PLACES_API_KEY") or "").strip()
    if not api_key:
        print("Missing GOOGLE_PLACES_API_KEY in environment or .env", file=sys.stderr)
        sys.exit(1)

    inp = os.path.abspath(args.input)
    if args.in_place:
        out = inp
        if not args.no_backup and os.path.isfile(inp):
            bak = inp + ".before_places.bak.csv"
            shutil.copy2(inp, bak)
            print(f"Backup: {bak}")
    elif args.output:
        out = os.path.abspath(args.output)
    else:
        out = os.path.join(os.path.dirname(inp), "items_from_places.csv")

    seeds = read_seed_rows(inp)
    if not seeds:
        print("No data rows in input CSV.", file=sys.stderr)
        sys.exit(1)

    used_ids: set[str] = set()
    out_rows: list[dict[str, str]] = []
    session = requests.Session()
    failed = 0

    for i, seed in enumerate(seeds):
        lat = float(seed["_lat"])
        lng = float(seed["_lng"])
        addr_hint = seed["_address"]
        orig = seed["_original"]

        places = nearby_search(session, api_key, lat, lng, args.radius)
        chosen = pick_place(places, used_ids)
        if not chosen:
            places = text_search_fallback(
                session, api_key, lat, lng, addr_hint, args.radius
            )
            chosen = pick_place(places, used_ids)

        if chosen:
            pid = chosen.get("id") or ""
            if pid:
                used_ids.add(pid)
            row = place_to_csv_row(chosen, addr_hint)
            out_rows.append(row)
            print(f"[{i + 1}/{len(seeds)}] OK: {row['Name'][:60]}")
        else:
            failed += 1
            print(
                f"[{i + 1}/{len(seeds)}] WARN: no place — keeping original row",
                file=sys.stderr,
            )
            out_rows.append(
                {
                    "Name": (orig.get("Name") or "").strip() or "UNKNOWN",
                    "Lat": seed["_lat"],
                    "Lng": seed["_lng"],
                    "Address": addr_hint,
                    "Features": (orig.get("Features") or "Places lookup: no match").strip(),
                    "Agoda": (orig.get("Agoda") or "").strip(),
                }
            )

        time.sleep(max(0.0, args.sleep))

    write_items_csv(out, out_rows)
    print(f"Wrote {len(out_rows)} rows -> {out}")
    if failed:
        print(f"Warnings: {failed} row(s) had no Places match (original data kept).")


if __name__ == "__main__":
    main()
