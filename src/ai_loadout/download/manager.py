"""Streamed HTTP downloader with resume, retry, allowlist, and SHA256 verification."""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse

from ..core import paths
from ..security.checksum import verify_sha256
from ..security.sources import is_official_source

ProgressFn = Callable[[int, int | None, str], None]
UrlOpenFn = Callable[..., object]

_CHUNK = 64 * 1024
_RETRYABLE = {408, 429, 500, 502, 503, 504}


class DownloadError(RuntimeError):
    """Raised when a download is blocked or fails after retries."""


def _default_dest(url: str) -> Path:
    parsed = urlparse(url)
    name = unquote(Path(parsed.path).name) or "download.bin"
    paths.ensure_dirs()
    return paths.data_dir() / "downloads" / name


def plan_download(
    url: str,
    *,
    dest: str | Path | None = None,
    expected_sha256: str | None = None,
) -> dict:
    """Read-only plan: official-source check, destination, resume hint."""

    official = is_official_source(url)
    target = Path(dest) if dest else _default_dest(url)
    part = target.with_suffix(target.suffix + ".part")
    resume_at = part.stat().st_size if part.is_file() else 0
    return {
        "ok": official,
        "url": url,
        "official_source": official,
        "dest": str(target),
        "part_path": str(part),
        "resume_bytes": resume_at,
        "verify_sha256": expected_sha256,
        "reason": None if official else "URL is not on the official-source allowlist",
    }


def _parse_total(headers) -> int | None:
    for key in ("Content-Length", "content-length"):
        raw = headers.get(key)
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
    cr = headers.get("Content-Range") or headers.get("content-range")
    if cr and "/" in cr:
        try:
            return int(cr.split("/")[-1])
        except ValueError:
            pass
    return None


def _request(url: str, resume_at: int, urlopen_fn: UrlOpenFn):
    req = urllib.request.Request(url)
    if resume_at > 0:
        req.add_header("Range", f"bytes={resume_at}-")
    return urlopen_fn(req, timeout=30)


def download_file(
    url: str,
    dest: str | Path | None = None,
    *,
    expected_sha256: str | None = None,
    on_progress: ProgressFn | None = None,
    urlopen_fn: UrlOpenFn | None = None,
    max_retries: int = 3,
    chunk_size: int = _CHUNK,
) -> dict:
    """Download ``url`` to ``dest`` with resume, retry, and optional hash verify."""

    if not is_official_source(url):
        raise DownloadError("refusing download: URL is not on the official-source allowlist")

    target = Path(dest) if dest else _default_dest(url)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    opener = urlopen_fn or urllib.request.urlopen

    resume_at = part.stat().st_size if part.is_file() else 0
    attempt = 0
    last_error = ""

    while attempt < max_retries:
        attempt += 1
        try:
            response = _request(url, resume_at, opener)
            status = getattr(response, "status", None) or response.getcode()
            headers = getattr(response, "headers", None) or response.info()

            if status == 416:
                part.unlink(missing_ok=True)
                resume_at = 0
                response.close()
                continue

            mode = "ab" if status == 206 and resume_at > 0 else "wb"
            if mode == "wb" and part.is_file():
                part.unlink(missing_ok=True)
                resume_at = 0

            total = _parse_total(headers)
            received = resume_at if mode == "ab" else 0

            with part.open(mode) as fh:
                while True:
                    block = response.read(chunk_size)
                    if not block:
                        break
                    fh.write(block)
                    received += len(block)
                    if on_progress:
                        on_progress(received, total, f"downloaded {received} bytes")
            response.close()

            if expected_sha256 and not verify_sha256(part, expected_sha256):
                part.unlink(missing_ok=True)
                raise DownloadError("checksum verification failed — file rejected")

            os.replace(part, target)
            result = {
                "ok": True,
                "url": url,
                "dest": str(target),
                "bytes": received,
                "verified": bool(expected_sha256),
                "attempts": attempt,
            }
            if on_progress:
                on_progress(received, total, "download complete")
            return result

        except urllib.error.HTTPError as exc:
            last_error = str(exc)
            if exc.code not in _RETRYABLE or attempt >= max_retries:
                raise DownloadError(last_error) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
            if attempt >= max_retries:
                raise DownloadError(last_error) from exc

        delay = min(2**attempt, 8)
        if on_progress:
            on_progress(resume_at, None, f"retry {attempt}/{max_retries} in {delay}s")
        time.sleep(delay)

    raise DownloadError(last_error or "download failed")


def download_with_bus(
    store,
    url: str,
    *,
    dest: str | Path | None = None,
    expected_sha256: str | None = None,
    urlopen_fn: UrlOpenFn | None = None,
) -> dict:
    """Dashboard action wrapper — streams progress to the event bus + install.log."""

    def _progress(received: int, total: int | None, message: str) -> None:
        pct = f" ({int(received * 100 / total)}%)" if total else ""
        store.bus.info(
            f"Download{pct}: {message}", kind="log", target="download", source="download"
        )

    store.bus.info(f"Starting download: {url}", kind="step", target="download", source="download")
    try:
        result = download_file(
            url,
            dest=dest,
            expected_sha256=expected_sha256,
            on_progress=_progress,
            urlopen_fn=urlopen_fn,
        )
    except DownloadError as exc:
        store.bus.error(str(exc), kind="log", target="download", source="download")
        return {"ok": False, "error": str(exc)}

    store.bus.success(
        f"Download saved to {result['dest']}",
        kind="step",
        target="download",
        source="download",
    )
    _append_install_log(f"download  {url}  ->  {result['dest']}")
    return result


def _append_install_log(line: str) -> None:
    try:
        paths.ensure_dirs()
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with paths.install_log().open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp}  {line}\n")
    except OSError:
        pass
