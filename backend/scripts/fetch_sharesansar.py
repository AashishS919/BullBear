"""Fetch daily OHLCV price history from sharesansar.com and write CSV.
"""
from __future__ import annotations

import argparse
import csv
import http.cookiejar
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE = "https://www.sharesansar.com"
HISTORY_URL = f"{BASE}/company-price-history"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# DataTables column order on the Price History tab.
COLUMNS = ["published_date", "open", "high", "low", "close",
           "per_change", "traded_quantity", "traded_amount"]

PAGE_SIZE = 50          # server rejects larger page sizes
REQUEST_DELAY = 0.8     # seconds between page requests
MAX_RETRIES = 3

DEFAULT_SYMBOLS = ["NABIL", "NICA", "NTC", "NRIC", "UPPER",
                   "CHCL", "VLBS", "SBL", "AHL", "ADBL"]

CSV_HEADER = ["symbol", "date", "open", "high", "low", "close",
              "volume", "percent_change", "traded_amount"]


class ShareSansarError(RuntimeError):
    """Raised when the site is unreachable or returns an unusable response."""


def _make_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", UA)]
    return opener


def company_context(opener, symbol: str) -> tuple[str, str]:
    """Return (csrf_token, companyid) for `symbol`, seeding the session cookie."""
    url = f"{BASE}/company/{symbol.lower()}"
    try:
        html = opener.open(url, timeout=30).read().decode("utf8", "replace")
    except urllib.error.HTTPError as exc:
        raise ShareSansarError(f"{symbol}: company page HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ShareSansarError(f"{symbol}: company page unreachable: {exc.reason}") from exc

    token = (re.search(r'<meta\s+name="_token"\s+content="([^"]+)"', html)
             or re.search(r'name="_token"\s+value="([^"]+)"', html))
    cid = re.search(r'id="companyid"[^>]*>\s*([0-9]+)\s*<', html)
    if not token or not cid:
        raise ShareSansarError(f"{symbol}: could not locate CSRF token / companyid "
                               f"(page layout may have changed)")
    return token.group(1), cid.group(1)


def _payload(company_id: str, start: int) -> bytes:
    p = {
        "draw": "1",
        "start": str(start),
        "length": str(PAGE_SIZE),
        "company": company_id,
        "search[value]": "",
        "search[regex]": "false",
        "order[0][column]": "0",
        "order[0][dir]": "desc",
    }
    for i, col in enumerate(COLUMNS):
        p[f"columns[{i}][data]"] = col
        p[f"columns[{i}][name]"] = ""
        p[f"columns[{i}][searchable]"] = "true"
        p[f"columns[{i}][orderable]"] = "true"
        p[f"columns[{i}][search][value]"] = ""
        p[f"columns[{i}][search][regex]"] = "false"
    return urllib.parse.urlencode(p).encode()


def fetch_page(opener, symbol: str, token: str, company_id: str, start: int) -> dict:
    req = urllib.request.Request(
        HISTORY_URL,
        data=_payload(company_id, start),
        headers={
            "User-Agent": UA,
            "X-CSRF-Token": token,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"{BASE}/company/{symbol.lower()}",
        },
    )
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            raw = opener.open(req, timeout=60).read().decode("utf8", "replace")
            return json.loads(raw)
        except (urllib.error.URLError, ValueError) as exc:
            last_exc = exc
            time.sleep(2 * (attempt + 1))
    raise ShareSansarError(f"{symbol}: page start={start} failed: {last_exc}")


def _num(value, default=0.0) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def normalize(symbol: str, row: dict) -> dict | None:
    """Map a ShareSansar row to the canonical CSV shape; None if unusable."""
    d = str(row.get("published_date") or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        return None
    close = _num(row.get("close"))
    if close <= 0:
        return None  # untraded / suspended day
    return {
        "symbol": symbol,
        "date": d,
        "open": round(_num(row.get("open"), close), 2),
        "high": round(_num(row.get("high"), close), 2),
        "low": round(_num(row.get("low"), close), 2),
        "close": round(close, 2),
        "volume": int(_num(row.get("traded_quantity"))),
        "percent_change": round(_num(row.get("per_change")), 2),
        "traded_amount": round(_num(row.get("traded_amount")), 2),
    }


def fetch_symbol(opener, symbol: str, start_date: str) -> list[dict]:
    """Page back through history (newest first) until older than `start_date`."""
    token, company_id = company_context(opener, symbol)
    rows: list[dict] = []
    start = 0
    total = None

    while True:
        data = fetch_page(opener, symbol, token, company_id, start)
        if total is None:
            total = int(data.get("recordsTotal") or 0)
        batch = data.get("data") or []
        if not batch:
            break

        exhausted = False
        for raw in batch:
            rec = normalize(symbol, raw)
            if rec is None:
                continue
            if rec["date"] < start_date:
                exhausted = True
                continue
            rows.append(rec)
        if exhausted:
            break

        start += PAGE_SIZE
        if total and start >= total:
            break
        print(f"    {symbol}: {len(rows)} rows so far ...", end="\r", flush=True)
        time.sleep(REQUEST_DELAY)

    # Dedupe on date (defensive) and return oldest-first.
    by_date = {r["date"]: r for r in rows}
    return [by_date[d] for d in sorted(by_date)]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Fetch OHLCV history from sharesansar.com")
    ap.add_argument("symbols", nargs="*", help=f"tickers (default: {' '.join(DEFAULT_SYMBOLS)})")
    ap.add_argument("--years", type=int, default=5, help="years of history (default 5)")
    ap.add_argument("--start", help="explicit start date YYYY-MM-DD (overrides --years)")
    ap.add_argument("--out", default="data/sharesansar", help="output directory")
    return ap.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    symbols = [s.upper() for s in args.symbols] or DEFAULT_SYMBOLS
    start_date = args.start or (date.today() - timedelta(days=365 * args.years + 2)).isoformat()
    out_dir = Path(args.out)

    print(f"ShareSansar OHLCV -> {out_dir}  (from {start_date})")
    opener = _make_opener()
    combined: list[dict] = []
    failures: list[str] = []

    for symbol in symbols:
        try:
            rows = fetch_symbol(opener, symbol, start_date)
        except ShareSansarError as exc:
            print(f"  {symbol}: FAILED - {exc}")
            failures.append(symbol)
            continue
        if not rows:
            print(f"  {symbol}: no rows in range")
            failures.append(symbol)
            continue
        write_csv(out_dir / f"{symbol}.csv", rows)
        combined.extend(rows)
        print(f"  {symbol}: {len(rows):>5} rows  {rows[0]['date']} -> {rows[-1]['date']}")
        time.sleep(REQUEST_DELAY)

    if combined:
        combined.sort(key=lambda r: (r["symbol"], r["date"]))
        write_csv(out_dir / "all_symbols.csv", combined)
        print(f"\nWrote {len(combined)} rows across {len(symbols) - len(failures)} symbols")
        print(f"Combined: {out_dir / 'all_symbols.csv'}")
    if failures:
        print(f"Failed: {', '.join(failures)}")
    return 1 if not combined else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
