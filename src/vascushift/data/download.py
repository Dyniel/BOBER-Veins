"""
Dataset download utilities (UBFC-rPPG, PhysioNet open projects).

Every download writes a ``_download_manifest.json`` next to the files with the
source URL, file sizes, SHA-256 checksums and a UTC timestamp, so that the
provenance of everything under ``data/raw`` can be audited later.

Raw data are never committed (``data/raw/`` is git-ignored). Restricted sources
(ESA HREDA, NASA LSDA, PURE, MMPD, ...) cannot be downloaded anonymously; see
``vascushift.data.registry`` and ``docs/data_audit.md`` for the access route.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional

USER_AGENT = "vascushift-data-download/0.1 (research; +https://github.com/Dyniel/BOBER-Veins)"

# Both mirrors are linked from the official UBFC-rPPG page
# https://sites.google.com/view/ybenezeth/ubfcrppg
# The Google Drive mirror often answers "Too many users have viewed or downloaded
# this file recently" for the ~1-3 GB videos, so the authors' OneDrive/SharePoint
# mirror (anonymous guest link) is the default.
UBFC_RPPG_DRIVE_FOLDER_ID = "1o0XU4gTIo46YfwaWjIgbtCncc-oF44Xk"
UBFC_RPPG_SHAREPOINT_LINK = (
    "https://univbourgogne-my.sharepoint.com/:f:/g/personal/yannick_benezeth_u-bourgogne_fr/"
    "IgDQvHIcDjiMSrzknzArGE25AVSjt4fjw11QgLpsJX2QPec?e=ySQtZt"
)
UBFC_RPPG_SHAREPOINT_WEB = "https://univbourgogne-my.sharepoint.com/personal/yannick_benezeth_u-bourgogne_fr"
UBFC_RPPG_SHAREPOINT_ROOT = "/personal/yannick_benezeth_u-bourgogne_fr/Documents/SharedDatasets/UBFC_DATASET"

PHYSIONET_FILES_URL = "https://physionet.org/files"


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _http_get(url: str, dest: Path, timeout: float = 120.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    tmp.replace(dest)


def _write_manifest(dest_dir: Path, payload: Dict) -> Path:
    path = dest_dir / "_download_manifest.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return path


# --------------------------------------------------------------------------- #
# PhysioNet (open-access projects)
# --------------------------------------------------------------------------- #
def download_physionet_project(
    slug: str,
    version: str,
    dest_root: Path,
    checksum: bool = True,
) -> Path:
    """
    Downloads an open-access PhysioNet project file-by-file, verifying each file
    against the project's ``SHA256SUMS.txt``. Existing files with a matching
    checksum are skipped, so the call is resumable.

    Returns the project directory ``dest_root/slug/version``.
    """
    base = f"{PHYSIONET_FILES_URL}/{slug}/{version}"
    dest = Path(dest_root) / slug / version
    dest.mkdir(parents=True, exist_ok=True)

    sums_path = dest / "SHA256SUMS.txt"
    _http_get(f"{base}/SHA256SUMS.txt", sums_path)
    expected: Dict[str, str] = {}
    for line in sums_path.read_text().splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            expected[parts[1].strip()] = parts[0].strip()

    files = []
    for rel, digest in sorted(expected.items()):
        target = dest / rel
        if target.exists() and (not checksum or sha256_file(target) == digest):
            status = "cached"
        else:
            _http_get(f"{base}/{rel}", target)
            status = "downloaded"
        actual = sha256_file(target) if checksum else None
        if checksum and actual != digest:
            raise IOError(f"Checksum mismatch for {target}: {actual} != {digest}")
        files.append({"path": rel, "bytes": target.stat().st_size, "sha256": actual, "status": status})

    _write_manifest(dest, {
        "dataset": f"physionet:{slug}/{version}",
        "source_url": base,
        "retrieved_utc": _utcnow(),
        "n_files": len(files),
        "total_bytes": sum(f["bytes"] for f in files),
        "checksum_verified": checksum,
        "files": files,
    })
    return dest


# --------------------------------------------------------------------------- #
# UBFC-rPPG (authors' public mirrors: OneDrive/SharePoint, Google Drive)
# --------------------------------------------------------------------------- #
class _SharePointGuest:
    """Minimal anonymous client for a SharePoint/OneDrive 'anyone with the link' folder."""

    def __init__(self, share_link: str, web: str):
        import http.cookiejar

        self.web = web.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        # Visiting the sharing link sets the FedAuth guest cookie.
        self.opener.open(urllib.request.Request(share_link, headers={"User-Agent": USER_AGENT}), timeout=60).read()

    def _json(self, api: str) -> Dict:
        req = urllib.request.Request(
            f"{self.web}/_api/web/{api}",
            headers={"Accept": "application/json;odata=nometadata", "User-Agent": USER_AGENT},
        )
        with self.opener.open(req, timeout=60) as r:
            return json.loads(r.read())

    def walk(self, folder: str) -> List[Dict]:
        from urllib.parse import quote

        d = self._json(f"GetFolderByServerRelativeUrl('{quote(folder)}')?$expand=Folders,Files")
        out = [{"server_path": f["ServerRelativeUrl"], "bytes": int(f["Length"])} for f in d["Files"]]
        for sub in d["Folders"]:
            out.extend(self.walk(sub["ServerRelativeUrl"]))
        return out

    def download(self, server_path: str, dest: Path, expected_bytes: int) -> None:
        """Streams a file with HTTP Range resume (``.part`` file)."""
        from urllib.parse import quote

        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        have = tmp.stat().st_size if tmp.exists() else 0
        if have > expected_bytes:  # corrupt leftover
            tmp.unlink()
            have = 0
        if have and have == expected_bytes:  # finished earlier, only the rename was missed
            tmp.replace(dest)
            return
        url = f"{self.web}/_api/web/GetFileByServerRelativeUrl('{quote(server_path)}')/$value"
        headers = {"User-Agent": USER_AGENT}
        if have:
            headers["Range"] = f"bytes={have}-"
        with self.opener.open(urllib.request.Request(url, headers=headers), timeout=300) as r:
            mode = "ab" if (have and r.status == 206) else "wb"
            with open(tmp, mode) as f:
                shutil.copyfileobj(r, f, length=1 << 22)
        if tmp.stat().st_size != expected_bytes:
            raise IOError(f"{server_path}: got {tmp.stat().st_size} bytes, expected {expected_bytes}")
        tmp.replace(dest)


def list_ubfc_rppg_files(source: str = "sharepoint") -> List[Dict]:
    """
    Lists every file of UBFC-rPPG as dicts with ``path`` (relative, e.g.
    ``DATASET_2/subject1/vid.avi``) and source-specific keys.
    """
    if source == "sharepoint":
        sp = _SharePointGuest(UBFC_RPPG_SHAREPOINT_LINK, UBFC_RPPG_SHAREPOINT_WEB)
        entries = sp.walk(UBFC_RPPG_SHAREPOINT_ROOT)
        for e in entries:
            e["path"] = e["server_path"].split(UBFC_RPPG_SHAREPOINT_ROOT + "/", 1)[1]
        return entries
    if source == "gdrive":
        import gdown  # optional dependency

        return [{"id": e.id, "path": e.path} for e in
                gdown.download_folder(id=UBFC_RPPG_DRIVE_FOLDER_ID, skip_download=True, quiet=True)]
    raise ValueError(f"unknown source {source!r}")


def download_ubfc_rppg(
    dest: Path,
    subsets: Iterable[str] = ("DATASET_2", "DATASET_1"),
    subjects: Optional[Iterable[str]] = None,
    include_videos: bool = True,
    source: str = "sharepoint",
    checksum: bool = True,
) -> Path:
    """
    Downloads UBFC-rPPG (Bobbia et al., Pattern Recognit. Lett. 2017) from the
    authors' public mirrors. Total size: ~92 GB (DATASET_2 ~75 GB, 42 videos of
    1.1-3.1 GB uncompressed AVI; DATASET_1 ~17 GB, 8 videos).

    Args:
        dest: target directory, e.g. ``data/raw/rppg/UBFC-rPPG``.
        subsets: which sub-datasets to fetch. Top-level docs (readme,
            agreement, reader scripts) are always fetched.
        subjects: optional subject folder names (e.g. ``["subject1"]``).
        include_videos: if False, only ground-truth files are fetched.
        source: ``"sharepoint"`` (default, authors' OneDrive) or ``"gdrive"``.

    Files already present with the expected size are skipped (resumable).
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    subsets = tuple(subsets)
    subjects = set(subjects) if subjects else None

    listing = list_ubfc_rppg_files(source)
    selected = []
    for e in listing:
        parts = e["path"].split("/")
        if len(parts) == 1:
            selected.append(e)
            continue
        if parts[0] not in subsets:
            continue
        if subjects is not None and parts[1] not in subjects:
            continue
        if not include_videos and parts[-1].endswith(".avi"):
            continue
        selected.append(e)
    # small files first so ground truth is usable while videos are still coming
    selected.sort(key=lambda e: (e["path"].endswith(".avi"), e["path"]))

    sp = _SharePointGuest(UBFC_RPPG_SHAREPOINT_LINK, UBFC_RPPG_SHAREPOINT_WEB) if source == "sharepoint" else None
    manifest_path = dest / "_download_manifest.json"
    known: Dict[str, Dict] = {}
    if manifest_path.exists():
        try:
            known = {f["path"]: f for f in json.loads(manifest_path.read_text()).get("files", [])}
        except (json.JSONDecodeError, KeyError):
            known = {}

    def _save_manifest() -> None:
        files = sorted(known.values(), key=lambda r: r["path"])
        _write_manifest(dest, {
            "dataset": "UBFC-rPPG",
            "source": source,
            "source_url": UBFC_RPPG_SHAREPOINT_LINK if source == "sharepoint"
            else f"https://drive.google.com/drive/folders/{UBFC_RPPG_DRIVE_FOLDER_ID}",
            "landing_page": "https://sites.google.com/view/ybenezeth/ubfcrppg",
            "retrieved_utc": _utcnow(),
            "n_files": len(files),
            "total_bytes": sum(f["bytes"] for f in files),
            "files": files,
        })

    for i, e in enumerate(selected, 1):
        target = dest / e["path"]
        expected = e.get("bytes")
        if target.exists() and (expected is None or target.stat().st_size == expected) and target.stat().st_size > 0:
            status = "cached"
        else:
            print(f"  [{i}/{len(selected)}] {e['path']} ({(expected or 0) / 1e9:.2f} GB)", flush=True)
            if sp is not None:
                for attempt in range(5):
                    try:
                        sp.download(e["server_path"], target, expected)
                        break
                    except Exception as exc:  # network hiccup: resume from .part
                        if attempt == 4:
                            raise
                        print(f"    retry {attempt + 1}: {exc}", flush=True)
                        sp = _SharePointGuest(UBFC_RPPG_SHAREPOINT_LINK, UBFC_RPPG_SHAREPOINT_WEB)
            else:
                import gdown

                out = gdown.download(id=e["id"], output=str(target), quiet=True, resume=True)
                if out is None or not target.exists():
                    raise IOError(f"gdown failed for {e['path']}; Drive quota? use source='sharepoint'")
            status = "downloaded"
        prev = known.get(e["path"], {})
        size = target.stat().st_size
        digest = prev.get("sha256") if (status == "cached" and prev.get("bytes") == size) else None
        if digest is None and checksum:
            digest = sha256_file(target)
        known[e["path"]] = {"path": e["path"], "bytes": size, "sha256": digest, "status": status}
        _save_manifest()
    return dest


# --------------------------------------------------------------------------- #
# GitHub data repositories (pinned to a commit for reproducibility)
# --------------------------------------------------------------------------- #
def download_github_repo_files(
    owner: str,
    repo: str,
    dest_root: Path,
    ref: Optional[str] = None,
    suffixes: Iterable[str] = (".csv", ".md", ".xlsx", ".rds", "LICENSE"),
) -> Path:
    """
    Downloads the data files of a public GitHub repository at a fixed commit
    (``ref`` = commit SHA; default: current HEAD, resolved and recorded in the
    manifest) into ``dest_root/repo``.
    """
    api = f"https://api.github.com/repos/{owner}/{repo}"

    def _api(url: str) -> Dict:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    meta = _api(api)
    sha = ref or _api(f"{api}/commits/{meta['default_branch']}")["sha"]
    tree = _api(f"{api}/git/trees/{sha}?recursive=1")["tree"]
    dest = Path(dest_root) / repo
    dest.mkdir(parents=True, exist_ok=True)
    files = []
    for node in tree:
        if node["type"] != "blob" or not node["path"].endswith(tuple(suffixes)):
            continue
        target = dest / node["path"]
        _http_get(f"https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{node['path']}", target)
        files.append({"path": node["path"], "bytes": target.stat().st_size, "sha256": sha256_file(target)})
    _write_manifest(dest, {
        "dataset": f"github:{owner}/{repo}",
        "source_url": f"https://github.com/{owner}/{repo}/tree/{sha}",
        "commit": sha,
        "license": (meta.get("license") or {}).get("spdx_id") or "NONE (all rights reserved by default)",
        "retrieved_utc": _utcnow(),
        "n_files": len(files),
        "total_bytes": sum(f["bytes"] for f in files),
        "files": files,
    })
    return dest
