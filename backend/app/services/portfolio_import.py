"""Parse an uploaded portfolio (CSV or PDF) and merge it into a user's holdings.
"""
import csv
import io
import re

from fastapi import HTTPException, status

# Header keyword groups (matched as substrings against normalized headers). "value"
# columns (e.g. "Value as of LTP") are always excluded so we never grab a total.
_SYMBOL_INCLUDES = ("scrip", "symbol", "stock", "ticker")
_QTY_INCLUDES = ("current balance", "balance", "quantity", "qty", "units", "shares")
_COST_INCLUDES = ("wacc", "average", "purchase", "cost", "rate")  # real cost basis
# Ordered fallbacks when there is no cost column: prefer LTP, then last close, then price.
_LTP_FALLBACKS = (("last transaction price", "ltp"), ("last closing", "closing"), ("price",))

_LTP_WARNING = (
    "No purchase/WACC price column found - used the last transaction price (LTP) as the "
    "cost basis, so unrealized P/L starts near zero. For real cost, upload Meroshare's "
    "WACC / purchase-source report instead."
)
# Header/summary tokens that are never a scrip symbol (used to skip the PDF header/total).
_STOPWORDS = {
    "scrip", "total", "last", "value", "price", "balance", "closing", "transaction",
    "current", "symbol", "quantity", "ltp", "as", "of", "sn",
}


def _to_number(raw) -> float:
    return float(str(raw).replace(",", "").strip())


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (header or "").lower()).strip()


def _clean_row(symbol, qty, avg_cost) -> tuple[dict | None, str | None]:
    """Validate one raw (symbol, qty, avg_cost) triple. Returns (row, None) on success,
    (None, warning) to skip-and-report, or (None, None) to skip silently (blank/total)."""
    sym = str(symbol or "").strip().upper()
    if not sym or _norm(sym) in _STOPWORDS or not re.fullmatch(r"[A-Z0-9]{1,12}", sym):
        return None, None  # blank line, header echo, or "Total :" row - skip quietly
    try:
        q = int(_to_number(qty))
        cost = _to_number(avg_cost)
    except (TypeError, ValueError):
        return None, f"Skipped '{sym}': quantity/cost not numeric ({qty!r}, {avg_cost!r})."
    if q <= 0:
        return None, f"Skipped '{sym}': quantity must be a positive whole number (got {qty!r})."
    if cost <= 0:
        return None, f"Skipped '{sym}': cost must be positive (got {avg_cost!r})."
    return {"symbol": sym, "qty": q, "avg_cost": round(cost, 2)}, None


def _find_column(cols: list[tuple[str, str]], includes, excludes=("value",)) -> str | None:
    """First original header whose normalized form contains any `includes` term and no
    `excludes` term. `cols` is [(normalized, original)] in file order."""
    for norm, orig in cols:
        if any(e in norm for e in excludes):
            continue
        if any(inc in norm for inc in includes):
            return orig
    return None


def _resolve_columns(fieldnames) -> tuple[str | None, str | None, str | None, bool]:
    """Map headers -> (symbol_col, qty_col, cost_col, cost_is_ltp)."""
    cols = [(_norm(h), h) for h in fieldnames if h is not None]
    sym = _find_column(cols, _SYMBOL_INCLUDES)
    qty = _find_column(cols, _QTY_INCLUDES)
    cost = _find_column(cols, _COST_INCLUDES)
    if cost:
        return sym, qty, cost, False
    for group in _LTP_FALLBACKS:  # no real cost column -> fall back to a market price
        col = _find_column(cols, group)
        if col:
            return sym, qty, col, True
    return sym, qty, None, False


def _parse_csv(content: bytes) -> tuple[list[dict], list[str]]:
    text = content.decode("utf-8-sig", errors="replace")
    try:  # sniff comma/tab/semicolon/pipe so Meroshare + Excel exports both work
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",\t;|")
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    except csv.Error:
        reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames or len(reader.fieldnames) < 2:
        return [], ["Could not read CSV columns. Expected headers like: symbol, qty, avg_cost."]

    sym_col, qty_col, cost_col, cost_is_ltp = _resolve_columns(reader.fieldnames)
    if not (sym_col and qty_col and cost_col):
        missing = [n for n, c in (("symbol", sym_col), ("quantity", qty_col), ("price", cost_col)) if not c]
        return [], [
            f"CSV is missing a {', '.join(missing)} column. Found: "
            f"{', '.join(reader.fieldnames)}."
        ]

    rows, warnings = [], []
    for line in reader:
        row, warn = _clean_row(line.get(sym_col), line.get(qty_col), line.get(cost_col))
        if row:
            rows.append(row)
        elif warn:
            warnings.append(warn)
    if rows and cost_is_ltp:
        warnings.append(_LTP_WARNING)
    return rows, warnings


def _parse_pdf_line(line: str) -> tuple[str, float, float] | None:
    """Best-effort parse of one PDF row. Handles a simple 'SYMBOL QTY COST' line and a
    Meroshare row 'S.N SCRIP BALANCE LASTCLOSE VALUE LTP VALUE' (qty=first number after
    the scrip; cost=LTP, the second-to-last number)."""
    tokens = line.strip().split()
    sym = next((t for t in tokens if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{1,11}", t)
                and _norm(t) not in _STOPWORDS), None)
    if sym is None:
        return None
    nums = []
    for t in tokens[tokens.index(sym) + 1:]:
        try:
            nums.append(_to_number(t))
        except ValueError:
            continue
    if not nums:
        return None
    qty = nums[0]
    if len(nums) >= 4:
        cost = nums[-2]      # Meroshare: ... LTP, ValueAsOfLTP
    elif len(nums) == 2:
        cost = nums[1]       # simple: SYMBOL QTY COST
    else:
        cost = nums[-1]
    return sym, qty, cost


def _parse_pdf(content: bytes) -> tuple[list[dict], list[str]]:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - dependency is in requirements.txt
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "PDF support unavailable: install 'pypdf' (pip install -r requirements.txt).",
        )
    try:
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # noqa: BLE001 - surface any malformed-PDF error cleanly
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not read PDF: {exc}")

    rows, warnings = [], []
    used_ltp = False
    for line in text.splitlines():
        parsed = _parse_pdf_line(line)
        if not parsed:
            continue
        sym, qty, cost = parsed
        used_ltp = used_ltp or len(line.split()) >= 6  # Meroshare-style multi-column row
        row, warn = _clean_row(sym, qty, cost)
        if row:
            rows.append(row)
        elif warn:
            warnings.append(warn)
    if not rows:
        warnings.append(
            "Could not find portfolio rows in the PDF. Broker/Meroshare PDF layouts vary - "
            "a CSV export is the reliable path."
        )
    elif used_ltp:
        warnings.append(_LTP_WARNING)
    return rows, warnings


def parse_portfolio(filename: str, content: bytes) -> tuple[list[dict], list[str]]:
    """Dispatch by file extension. Returns (cleaned_rows, warnings)."""
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty.")
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return _parse_csv(content)
    if name.endswith(".pdf"):
        return _parse_pdf(content)
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Unsupported file type. Upload a .csv or .pdf portfolio.",
    )


def import_holdings(*, holdings, market, user_id: str, rows: list[dict]) -> tuple[int, list[str]]:
    """Merge parsed rows into the user's holdings. Returns (imported_count, warnings).
    Cash is untouched; unknown symbols are still imported but flagged."""
    warnings: list[str] = []
    for r in rows:
        if market.get_quote(r["symbol"]) is None:
            warnings.append(f"'{r['symbol']}' is not in the market universe; imported without a live price.")
        holdings.upsert(user_id, r["symbol"], r["qty"], r["avg_cost"])
    return len(rows), warnings
