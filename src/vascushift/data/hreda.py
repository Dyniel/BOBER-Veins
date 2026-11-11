"""
ESA HREDA (Human and Robotic Exploration Data Archive) client.

Uses the public IVOA TAP endpoint (no login) for *metadata*. Downloading files
(even public ones) requires an HREDA/ESA account: anonymous requests to
``/hreda-sl-tap/data?retrieval_type=PRODUCT`` return HTTP 403 "Anonymous users
cannot download data. Please LOG IN". Medically sensitive investigations need
an additional data-access request.
"""

from __future__ import annotations

import datetime as _dt
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List

HREDA_TAP_SYNC = "https://hreda.esac.esa.int/hreda-sl-tap/tap/sync"
USER_AGENT = "vascushift-data-audit/0.1"

# Investigations relevant to VascuShift (see docs/data_audit.md)
RELEVANT_INVESTIGATIONS = [
    "HeadwardFluidShift_PARA",      # PFC82 2023, IJV vs gravity - target dataset
    "Drain_Brain_ISS",              # jugular outflow plethysmography on ISS
    "Hemo_BRIM",                    # BRACE 2023 bed rest, blood volume / orthostatic tolerance
    "Cocktail_BRIM", "MNX_BRIM", "NUC_BRIM", "BRAG_BRIM", "RSL_BRIM",  # HDT bed-rest data blank books
    "MobileHR_ISS",                 # heart-rate monitor on ISS
    "EPO_UznanskiVideos_ignis_ISS",  # astronaut video in microgravity (no physiological GT)
]


def tap_query(adql: str, maxrec: int = 10000, timeout: float = 60.0) -> List[Dict]:
    data = urllib.parse.urlencode({
        "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "MAXREC": maxrec, "QUERY": adql,
    }).encode()
    req = urllib.request.Request(HREDA_TAP_SYNC, data=data, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    cols = [m["name"] for m in d["metadata"]]
    return [dict(zip(cols, row)) for row in d["data"]]


def _quote_list(items: List[str]) -> str:
    return ", ".join("'" + i.replace("'", "''") + "'" for i in items)


def investigation_status(acronyms: List[str] = RELEVANT_INVESTIGATIONS) -> List[Dict]:
    """Availability flags and file counts per investigation."""
    inv = tap_query(
        "SELECT investigation_oid, investigation_unique_acronym, investigation_title, investigation_doi, "
        "platform_name, mission_name, start_date, end_date, data_available, ancillary_data_available, "
        "medical_sensitive, team_coordinator_name, last_update_date "
        f"FROM hreda.v_investigation WHERE investigation_unique_acronym IN ({_quote_list(acronyms)})"
    )
    files = tap_query(
        "SELECT investigation_unique_acronym, COUNT(*) AS n_files, SUM(file_size) AS total_bytes "
        f"FROM hreda.v_file_metadata WHERE investigation_unique_acronym IN ({_quote_list(acronyms)}) "
        "GROUP BY investigation_unique_acronym"
    )
    fmap = {f["investigation_unique_acronym"]: f for f in files}
    for r in inv:
        f = fmap.get(r["investigation_unique_acronym"], {})
        r["n_files"] = int(f.get("n_files") or 0)
        r["total_bytes"] = int(f.get("total_bytes") or 0)
    return inv


def investigation_files(acronym: str) -> List[Dict]:
    return tap_query(
        "SELECT file_metadata_oid, file_name, relative_path, file_format, file_size, product_type, "
        "processing_level, access_granted, security_level "
        f"FROM hreda.v_file_metadata WHERE investigation_unique_acronym = '{acronym}'"
    )


def save_hreda_snapshot(out_dir: Path, acronyms: List[str] = RELEVANT_INVESTIGATIONS) -> Path:
    """Saves investigation status + file lists as JSON (small, safe to commit)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status = investigation_status(acronyms)
    snapshot = {
        "retrieved_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endpoint": HREDA_TAP_SYNC,
        "investigations": status,
        "files": {s["investigation_unique_acronym"]: investigation_files(s["investigation_unique_acronym"])
                  for s in status if s["n_files"] and s["n_files"] <= 500},
    }
    path = out_dir / "hreda_snapshot.json"
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, default=str))
    return path
