"""Portfolio import endpoint: CSV/PDF parsing, merge semantics, cash untouched."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register(email: str) -> str:
    r = client.post("/api/auth/register", json={
        "name": "Importer", "email": email, "password": "Trader@123",
    })
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _build_pdf(lines: list[str]) -> bytes:
    """Minimal single-page PDF with the given text lines (valid xref, pypdf-readable)."""
    parts = []
    for i, line in enumerate(lines):
        parts.append(f"({line}) Tj" if i == 0 else f"0 -20 Td ({line}) Tj")
    stream = ("BT /F1 12 Tf 72 700 Td " + " ".join(parts) + " ET").encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref_pos = len(pdf)
    n = len(objs) + 1
    pdf += b"xref\n0 " + str(n).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        pdf += ("%010d 00000 n \n" % off).encode()
    pdf += b"trailer\n<< /Size " + str(n).encode() + b" /Root 1 0 R >>\n"
    pdf += b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    return pdf


def _positions(token: str) -> dict:
    r = client.get("/api/portfolio", headers=_auth(token))
    assert r.status_code == 200, r.text
    body = r.json()
    return {p["symbol"]: p for p in body["positions"]}, body["summary"]


def test_csv_import_merges_and_skips_bad_rows():
    token = _register("csvimport@example.com")
    _, summary0 = _positions(token)
    cash_before = summary0["cash"]

    csv_bytes = b"symbol,qty,avg_cost\nNABIL,10,500\nNTC,5,900\nFOO,abc,100\n"
    r = client.post(
        "/api/portfolio/import",
        headers=_auth(token),
        files={"file": ("holdings.csv", csv_bytes, "text/csv")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported"] == 2
    assert body["skipped"] == 1
    assert any("FOO" in w for w in body["warnings"])

    positions, summary = _positions(token)
    assert positions["NABIL"]["qty"] == 10 and positions["NABIL"]["avg_cost"] == 500
    assert positions["NTC"]["qty"] == 5 and positions["NTC"]["avg_cost"] == 900
    # Cash is untouched by an import.
    assert summary["cash"] == cash_before


def test_csv_reimport_overwrites_matching_symbol():
    token = _register("csvmerge@example.com")
    client.post(
        "/api/portfolio/import",
        headers=_auth(token),
        files={"file": ("a.csv", b"symbol,qty,avg_cost\nNABIL,10,500\nNTC,5,900\n", "text/csv")},
    )
    # Re-import NABIL only with new numbers: NABIL overwritten, NTC kept (merge).
    r = client.post(
        "/api/portfolio/import",
        headers=_auth(token),
        files={"file": ("b.csv", b"symbol,quantity,average_cost\nNABIL,20,600\n", "text/csv")},
    )
    assert r.status_code == 200, r.text
    positions, _ = _positions(token)
    assert positions["NABIL"]["qty"] == 20 and positions["NABIL"]["avg_cost"] == 600
    assert positions["NTC"]["qty"] == 5


def test_pdf_import():
    token = _register("pdfimport@example.com")
    pdf = _build_pdf(["NABIL 10 500", "NTC 5 900", "some header line ignored"])
    r = client.post(
        "/api/portfolio/import",
        headers=_auth(token),
        files={"file": ("holdings.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 2
    positions, _ = _positions(token)
    assert positions["NABIL"]["qty"] == 10
    assert positions["NTC"]["qty"] == 5


def test_meroshare_csv_import():
    """Real Meroshare holdings export: 'Scrip'/'Current Balance' columns, no cost basis
    (LTP used as fallback), and a 'Total :' summary row that must be ignored."""
    token = _register("meroshare@example.com")
    csv_bytes = (
        b"S.N,Scrip,Current Balance,Last Closing Price,Value as of Last Closing Price,"
        b"Last Transaction Price (LTP),Value as of LTP\n"
        b"1,VLBS,10,685,6850,695,6950\n"
        b"2,NABIL,4,510,2040,520,2080\n"
        b"Total :,,,,8890,,9030\n"
    )
    r = client.post(
        "/api/portfolio/import",
        headers=_auth(token),
        files={"file": ("meroshare.csv", csv_bytes, "text/csv")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported"] == 2  # VLBS + NABIL, the Total row skipped
    assert any("LTP" in w or "cost basis" in w for w in body["warnings"])  # LTP-fallback note

    positions, _ = _positions(token)
    # qty comes from Current Balance; cost basis falls back to LTP.
    assert positions["VLBS"]["qty"] == 10 and positions["VLBS"]["avg_cost"] == 695
    assert positions["NABIL"]["qty"] == 4 and positions["NABIL"]["avg_cost"] == 520


def test_meroshare_pdf_import():
    token = _register("meropdf@example.com")
    pdf = _build_pdf([
        "S.N Scrip Current Balance Last Closing Price Value LTP Value",
        "1 VLBS 10 685 6850 695 6950",
        "2 NABIL 4 510 2040 520 2080",
        "Total : 8890 9030",
    ])
    r = client.post(
        "/api/portfolio/import",
        headers=_auth(token),
        files={"file": ("meroshare.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 2
    positions, _ = _positions(token)
    assert positions["VLBS"]["qty"] == 10 and positions["VLBS"]["avg_cost"] == 695
    assert positions["NABIL"]["qty"] == 4 and positions["NABIL"]["avg_cost"] == 520


def test_unsupported_extension_rejected():
    token = _register("badext@example.com")
    r = client.post(
        "/api/portfolio/import",
        headers=_auth(token),
        files={"file": ("holdings.txt", b"NABIL 10 500", "text/plain")},
    )
    assert r.status_code == 422


def test_empty_file_rejected():
    token = _register("empty@example.com")
    r = client.post(
        "/api/portfolio/import",
        headers=_auth(token),
        files={"file": ("holdings.csv", b"", "text/csv")},
    )
    assert r.status_code == 400


def test_import_requires_auth():
    r = client.post(
        "/api/portfolio/import",
        files={"file": ("holdings.csv", b"symbol,qty,avg_cost\nNABIL,10,500\n", "text/csv")},
    )
    assert r.status_code == 401
