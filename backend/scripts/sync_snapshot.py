"""Export / import a fixed data snapshot so two machines show identical data.
"""
import argparse
import gzip
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bson import json_util  # noqa: E402  (ships with pymongo)
from pymongo import ASCENDING, MongoClient  # noqa: E402

from app.config import get_settings  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT_DIR = REPO_ROOT / "snapshot"
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
CANDLES_FILE = "market_candles.json.gz"
ARTIFACTS_FILE = "ml_artifacts.zip"


def _connect():
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=4000)
    client.admin.command("ping")  # fail fast with a clear error if Mongo is down
    return client, client[settings.mongo_db], settings


# --------------------------------------------------------------------------- export
def export_snapshot(snapshot_dir: Path) -> None:
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # 1) market_candles -> gzipped extended-JSON (json_util preserves Mongo types).
    client, db, settings = _connect()
    docs = list(db.market_candles.find({}))
    for d in docs:
        d.pop("_id", None)  # let Mongo assign fresh _ids on import
    out = snapshot_dir / CANDLES_FILE
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        fh.write(json_util.dumps(docs))
    symbols = sorted({d.get("symbol") for d in docs})
    print(f"Exported {len(docs)} candles ({len(symbols)} symbols: {', '.join(symbols)})")
    print(f"  -> {out}")
    client.close()

    # 2) ml/artifacts/ -> zip.
    if not ARTIFACTS_DIR.exists():
        print(f"WARNING: {ARTIFACTS_DIR} does not exist; skipping ML artifacts.")
    else:
        zpath = snapshot_dir / ARTIFACTS_FILE
        count = 0
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(ARTIFACTS_DIR.rglob("*")):
                if f.is_file():
                    zf.write(f, f.relative_to(ARTIFACTS_DIR))
                    count += 1
        print(f"Exported {count} ML artifact files -> {zpath}")

    print("\nSnapshot ready. Move the 'snapshot/' folder to the other machine, then run:")
    print("  venv\\Scripts\\python.exe scripts\\sync_snapshot.py import")


# --------------------------------------------------------------------------- import
def import_snapshot(snapshot_dir: Path) -> None:
    candles_path = snapshot_dir / CANDLES_FILE
    if not candles_path.exists():
        sys.exit(f"ERROR: {candles_path} not found. Run 'export' on the source machine first.")

    # 1) Restore market_candles (replace existing so the two machines match exactly).
    client, db, settings = _connect()
    with gzip.open(candles_path, "rt", encoding="utf-8") as fh:
        docs = json_util.loads(fh.read())
    col = db.market_candles
    col.drop()
    if docs:
        col.insert_many(docs)
    col.create_index([("symbol", ASCENDING), ("date", ASCENDING)], unique=True)
    symbols = sorted({d.get("symbol") for d in docs})
    print(f"Imported {len(docs)} candles into '{settings.mongo_db}.market_candles' "
          f"({len(symbols)} symbols: {', '.join(symbols)})")
    client.close()

    # 2) Restore ml/artifacts/.
    zpath = snapshot_dir / ARTIFACTS_FILE
    if not zpath.exists():
        print(f"WARNING: {zpath} not found; skipping ML artifacts "
              "(Prediction-vs-Actual will not match until you copy these).")
    else:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(ARTIFACTS_DIR)
            count = len(zf.namelist())
        print(f"Imported {count} ML artifact files -> {ARTIFACTS_DIR}")

    print("\nImport complete. Restart the backend so it serves the synced data.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export/import a BullBear data snapshot.")
    parser.add_argument("action", choices=["export", "import"])
    parser.add_argument(
        "--dir", type=Path, default=DEFAULT_SNAPSHOT_DIR,
        help=f"Snapshot directory (default: {DEFAULT_SNAPSHOT_DIR})",
    )
    args = parser.parse_args()
    if args.action == "export":
        export_snapshot(args.dir)
    else:
        import_snapshot(args.dir)


if __name__ == "__main__":
    main()
