#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Allowlisted Maqam static server and bounded same-origin Dify proxy.

Configuration comes only from process environment. Never place credentials in
source, served configuration files or logs. Run with ``python server.py``.
"""

from collections import OrderedDict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import binascii
import email.parser
import email.policy
import ipaddress
import json
import logging
import math
import mimetypes
import os
from pathlib import Path
import re
import socket
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib

BASE_DIR = Path(__file__).resolve().parent
APP_FILE = "maqamooo.html"
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
DIFY_API_URL = os.environ.get("DIFY_API_URL", "https://api.dify.ai/v1")
PORT = os.environ.get("PORT", "5000")
MAX_BODY_BYTES = 16_384
MAX_IMAGE_BYTES = 2_097_152
MAX_UPLOAD_BODY_BYTES = 2_850_000
MAX_QUERY_CHARS = 4_000
MAX_UPSTREAM_BYTES = 1_048_576
UPSTREAM_TIMEOUT_SECONDS = 20
CLIENT_TIMEOUT_SECONDS = 10
RATE_LIMIT_COUNT = 20
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_RATE_IDENTITIES = 4_096
MAX_REQUEST_WORKERS = 64
PUBLIC_ASSET_EXTENSIONS = frozenset({
    ".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".webp", ".avif",
    ".gif", ".ico", ".woff", ".woff2", ".ttf", ".mp4", ".webm", ".mp3",
    ".ogg", ".wav",
})
# New corpus assets are a filename manifest, never an extension/prefix grant.
ROUND3_PUBLIC_PATHS = frozenset({
    "/data/languages.json", "/data/lectures.json", "/data/quizzes.json",
    "/data/summaries.json", "/data/haram-schedule.json", "/data/books.json",
    "/data/subtitles-unverified.json",
    "/assets/brand/maqam.png", "/assets/brand/favicon-32.png",
    "/assets/brand/favicon-192.png", "/assets/brand/touch-icon.png",
    "/assets/brand/apple-touch-icon.png",
    *{f"/assets/books/book-{number}.pdf" for number in range(1, 8)},
    *{f"/assets/book-covers/book-{number}.png" for number in range(1, 8)},
    *{f"/data/book-indexes/book-{number}.json" for number in range(1, 8)},
})
ROUND4_PUBLIC_PATHS = frozenset({'/assets/books/book-8.pdf','/assets/books/book-9.pdf','/assets/book-covers/book-8.png','/assets/book-covers/book-9.png','/data/book-indexes/book-8.json','/data/book-indexes/book-9.json','/assets/ocr/ara.traineddata.gz', '/assets/pdfjs/cmaps/GBKp-EUC-H.bcmap', '/assets/pdfjs/cmaps/90pv-RKSJ-H.bcmap', '/assets/pdfjs/cmaps/GBT-EUC-V.bcmap', '/assets/pdfjs/cmaps/Adobe-CNS1-6.bcmap', '/assets/pdfjs/cmaps/UniJISX0213-UTF32-H.bcmap', '/assets/pdfjs/wasm/LICENSE_PDFJS_JBIG2', '/assets/pdfjs/cmaps/UniGB-UTF16-V.bcmap', '/assets/pdfjs/standard_fonts/FoxitSymbol.pfb', '/assets/pdfjs/standard_fonts/FoxitFixedBold.pfb', '/assets/pdfjs/standard_fonts/FoxitFixedItalic.pfb', '/assets/pdfjs/standard_fonts/FoxitSerifBold.pfb', '/assets/pdfjs/cmaps/NWP-V.bcmap', '/assets/pdfjs/wasm/LICENSE_QCMS', '/assets/pdfjs/cmaps/GBKp-EUC-V.bcmap', '/assets/pdfjs/cmaps/KSC-Johab-V.bcmap', '/assets/pdfjs/cmaps/UniJIS2004-UTF32-H.bcmap', '/assets/pdfjs/cmaps/UniKS-UTF8-H.bcmap', '/assets/pdfjs/cmaps/Add-RKSJ-H.bcmap', '/assets/pdfjs/standard_fonts/FoxitSerifBoldItalic.pfb', '/assets/pdfjs/standard_fonts/FoxitDingbats.pfb', '/assets/pdfjs/cmaps/90pv-RKSJ-V.bcmap', '/assets/pdfjs/cmaps/CNS-EUC-H.bcmap', '/assets/pdfjs/cmaps/UniGB-UTF16-H.bcmap', '/assets/pdfjs/cmaps/UniJIS-UTF32-V.bcmap', '/assets/pdfjs/cmaps/Adobe-CNS1-1.bcmap', '/assets/pdfjs/wasm/qcms_bg.wasm', '/assets/pdfjs/cmaps/UniCNS-UTF8-V.bcmap', '/assets/pdfjs/cmaps/CNS1-H.bcmap', '/assets/pdfjs/cmaps/EUC-V.bcmap', '/assets/pdfjs/cmaps/UniKS-UTF32-H.bcmap', '/assets/pdfjs/cmaps/HKdla-B5-V.bcmap', '/assets/pdfjs/cmaps/Roman.bcmap', '/assets/pdfjs/cmaps/Ext-H.bcmap', '/assets/pdfjs/cmaps/UniJIS2004-UTF8-H.bcmap', '/assets/pdfjs/cmaps/83pv-RKSJ-H.bcmap', '/assets/pdfjs/cmaps/Adobe-Japan1-4.bcmap', '/assets/pdfjs/cmaps/ETHK-B5-H.bcmap', '/assets/pdfjs/cmaps/KSCpc-EUC-H.bcmap', '/assets/pdfjs/cmaps/UniJISPro-UCS2-V.bcmap', '/assets/pdfjs/wasm/openjpeg_nowasm_fallback.js', '/assets/pdfjs/cmaps/90ms-RKSJ-V.bcmap', '/assets/pdfjs/cmaps/Add-V.bcmap', '/assets/pdfjs/cmaps/Adobe-Korea1-2.bcmap', '/assets/pdfjs/cmaps/78-H.bcmap', '/assets/pdfjs/cmaps/Adobe-CNS1-0.bcmap', '/assets/pdfjs/cmaps/90ms-RKSJ-H.bcmap', '/assets/pdfjs/cmaps/KSCms-UHC-H.bcmap', '/assets/pdfjs/cmaps/EUC-H.bcmap', '/assets/pdfjs/cmaps/LICENSE', '/assets/pdfjs/wasm/LICENSE_PDFJS_QCMS', '/assets/pdfjs/cmaps/UniKS-UTF16-V.bcmap', '/assets/pdfjs/cmaps/ETenms-B5-V.bcmap', '/assets/pdfjs/cmaps/B5-V.bcmap', '/assets/pdfjs/cmaps/KSC-H.bcmap', '/assets/pdfjs/cmaps/UniJIS-UTF8-H.bcmap', '/assets/pdfjs/cmaps/UniKS-UTF32-V.bcmap', '/assets/pdfjs/cmaps/Adobe-GB1-4.bcmap', '/assets/pdfjs/cmaps/GB-EUC-H.bcmap', '/assets/pdfjs/cmaps/Adobe-Japan1-6.bcmap', '/assets/pdfjs/cmaps/Adobe-Korea1-1.bcmap', '/assets/pdfjs/cmaps/KSCms-UHC-V.bcmap', '/assets/pdfjs/cmaps/GBpc-EUC-V.bcmap', '/assets/pdfjs/cmaps/UniJISX02132004-UTF32-H.bcmap', '/assets/pdfjs/cmaps/HKm314-B5-V.bcmap', '/assets/pdfjs/cmaps/Adobe-GB1-2.bcmap', '/assets/pdfjs/cmaps/Adobe-Japan1-3.bcmap', '/assets/pdfjs/cmaps/NWP-H.bcmap', '/assets/pdfjs/cmaps/78-V.bcmap', '/assets/pdfjs/cmaps/UniGB-UTF8-V.bcmap', '/assets/pdfjs/cmaps/Adobe-Japan1-1.bcmap', '/assets/pdfjs/cmaps/UniCNS-UTF32-H.bcmap', '/assets/pdfjs/cmaps/KSC-V.bcmap', '/assets/pdfjs/cmaps/78ms-RKSJ-V.bcmap', '/assets/pdfjs/wasm/openjpeg.wasm', '/assets/pdfjs/cmaps/UniCNS-UTF16-V.bcmap', '/assets/pdfjs/cmaps/UniJIS-UTF16-H.bcmap', '/assets/pdfjs/cmaps/Ext-RKSJ-H.bcmap', '/assets/pdfjs/cmaps/HKm471-B5-H.bcmap', '/assets/pdfjs/cmaps/UniCNS-UCS2-V.bcmap', '/assets/pdfjs/cmaps/ETHK-B5-V.bcmap', '/assets/pdfjs/cmaps/ETen-B5-V.bcmap', '/assets/pdfjs/cmaps/UniGB-UCS2-H.bcmap', '/assets/pdfjs/cmaps/UniCNS-UTF8-H.bcmap', '/assets/pdfjs/wasm/jbig2.wasm', '/assets/pdfjs/cmaps/HKdlb-B5-V.bcmap', '/assets/pdfjs/cmaps/Adobe-Japan1-2.bcmap', '/assets/pdfjs/cmaps/Katakana.bcmap', '/assets/pdfjs/cmaps/GBK2K-H.bcmap', '/assets/pdfjs/wasm/LICENSE_PDFJS_OPENJPEG', '/assets/pdfjs/wasm/LICENSE_JBIG2', '/assets/pdfjs/cmaps/Add-H.bcmap', '/assets/pdfjs/cmaps/B5-H.bcmap', '/assets/pdfjs/cmaps/UniJISPro-UTF8-V.bcmap', '/assets/pdfjs/cmaps/GB-H.bcmap', '/assets/pdfjs/cmaps/Adobe-GB1-5.bcmap', '/assets/pdfjs/cmaps/H.bcmap', '/assets/pdfjs/cmaps/HKm471-B5-V.bcmap', '/assets/pdfjs/cmaps/Adobe-Japan1-5.bcmap', '/assets/pdfjs/cmaps/CNS-EUC-V.bcmap', '/assets/pdfjs/cmaps/Adobe-CNS1-UCS2.bcmap', '/assets/pdfjs/cmaps/Adobe-Japan1-0.bcmap', '/assets/pdfjs/cmaps/UniCNS-UCS2-H.bcmap', '/assets/pdfjs/standard_fonts/LiberationSans-Bold.ttf', '/assets/pdfjs/cmaps/UniCNS-UTF16-H.bcmap', '/assets/pdfjs/cmaps/78ms-RKSJ-H.bcmap', '/assets/pdfjs/cmaps/CNS1-V.bcmap', '/assets/pdfjs/cmaps/UniGB-UTF32-H.bcmap', '/assets/pdfjs/cmaps/GBK-EUC-V.bcmap', '/assets/pdfjs/cmaps/GBTpc-EUC-H.bcmap', '/assets/pdfjs/cmaps/UniJIS-UTF8-V.bcmap', '/assets/pdfjs/wasm/quickjs-eval.js', '/assets/pdfjs/cmaps/Adobe-CNS1-2.bcmap', '/assets/pdfjs/cmaps/UniKS-UTF8-V.bcmap', '/assets/pdfjs/cmaps/Ext-RKSJ-V.bcmap', '/assets/pdfjs/cmaps/UniJIS-UCS2-V.bcmap', '/assets/pdfjs/cmaps/UniJISX0213-UTF32-V.bcmap', '/assets/pdfjs/standard_fonts/LiberationSans-BoldItalic.ttf', '/assets/pdfjs/cmaps/GBK-EUC-H.bcmap', '/assets/pdfjs/cmaps/GBT-V.bcmap', '/assets/pdfjs/cmaps/UniGB-UTF8-H.bcmap', '/assets/pdfjs/cmaps/HKgccs-B5-H.bcmap', '/assets/pdfjs/cmaps/Adobe-GB1-1.bcmap', '/assets/pdfjs/cmaps/B5pc-H.bcmap', '/assets/pdfjs/cmaps/KSCms-UHC-HW-H.bcmap', '/assets/pdfjs/standard_fonts/LiberationSans-Regular.ttf', '/assets/pdfjs/standard_fonts/LICENSE_FOXIT', '/assets/pdfjs/cmaps/Adobe-Japan1-UCS2.bcmap', '/assets/pdfjs/cmaps/HKm314-B5-H.bcmap', '/assets/pdfjs/cmaps/Hiragana.bcmap', '/assets/pdfjs/cmaps/RKSJ-H.bcmap', '/assets/pdfjs/cmaps/GB-EUC-V.bcmap', '/assets/pdfjs/cmaps/UniJIS-UTF32-H.bcmap', '/assets/pdfjs/cmaps/UniJIS-UCS2-HW-H.bcmap', '/assets/pdfjs/cmaps/UniJIS2004-UTF16-V.bcmap', '/assets/pdfjs/standard_fonts/LICENSE_LIBERATION', '/assets/pdfjs/cmaps/UniJIS-UTF16-V.bcmap', '/assets/pdfjs/standard_fonts/FoxitFixed.pfb', '/assets/pdfjs/cmaps/GBK2K-V.bcmap', '/assets/pdfjs/cmaps/Adobe-GB1-3.bcmap', '/assets/pdfjs/cmaps/KSCms-UHC-HW-V.bcmap', '/assets/pdfjs/cmaps/GBT-EUC-H.bcmap', '/assets/pdfjs/cmaps/KSC-Johab-H.bcmap', '/assets/pdfjs/standard_fonts/LiberationSans-Italic.ttf', '/assets/pdfjs/standard_fonts/FoxitSerifItalic.pfb', '/assets/pdfjs/pdf.worker.6.4.299.min.mjs', '/assets/pdfjs/cmaps/Adobe-Korea1-0.bcmap', '/assets/pdfjs/wasm/jbig2_nowasm_fallback.js', '/assets/pdfjs/cmaps/Adobe-Korea1-UCS2.bcmap', '/assets/pdfjs/cmaps/78-RKSJ-V.bcmap', '/assets/pdfjs/cmaps/Hankaku.bcmap', '/assets/pdfjs/cmaps/HKscs-B5-V.bcmap', '/assets/pdfjs/cmaps/Adobe-CNS1-5.bcmap', '/assets/pdfjs/cmaps/HKdla-B5-H.bcmap', '/assets/pdfjs/cmaps/Adobe-GB1-0.bcmap', '/assets/pdfjs/cmaps/UniJIS2004-UTF16-H.bcmap', '/assets/pdfjs/cmaps/RKSJ-V.bcmap', '/assets/pdfjs/cmaps/Adobe-CNS1-4.bcmap', '/assets/pdfjs/cmaps/UniCNS-UTF32-V.bcmap', '/assets/pdfjs/cmaps/78-EUC-H.bcmap', '/assets/pdfjs/cmaps/HKdlb-B5-H.bcmap', '/assets/pdfjs/cmaps/CNS2-H.bcmap', '/assets/pdfjs/cmaps/HKgccs-B5-V.bcmap', '/assets/pdfjs/cmaps/90msp-RKSJ-V.bcmap', '/assets/pdfjs/cmaps/UniJIS-UCS2-HW-V.bcmap', '/assets/pdfjs/cmaps/UniJIS2004-UTF32-V.bcmap', '/assets/pdfjs/cmaps/ETenms-B5-H.bcmap', '/assets/pdfjs/cmaps/V.bcmap', '/assets/pdfjs/wasm/LICENSE_OPENJPEG', '/assets/pdfjs/cmaps/90msp-RKSJ-H.bcmap', '/assets/pdfjs/cmaps/WP-Symbol.bcmap', '/assets/pdfjs/cmaps/KSCpc-EUC-V.bcmap', '/assets/pdfjs/cmaps/CNS2-V.bcmap', '/assets/pdfjs/cmaps/ETen-B5-H.bcmap', '/assets/pdfjs/LICENSE', '/assets/pdfjs/cmaps/UniKS-UCS2-H.bcmap', '/assets/pdfjs/cmaps/UniKS-UCS2-V.bcmap', '/assets/pdfjs/cmaps/GBT-H.bcmap', '/assets/pdfjs/cmaps/GBTpc-EUC-V.bcmap', '/assets/pdfjs/cmaps/KSC-EUC-H.bcmap', '/assets/pdfjs/cmaps/UniJIS2004-UTF8-V.bcmap', '/assets/pdfjs/cmaps/HKscs-B5-H.bcmap', '/assets/pdfjs/cmaps/KSC-EUC-V.bcmap', '/assets/pdfjs/cmaps/B5pc-V.bcmap', '/assets/pdfjs/cmaps/GBpc-EUC-H.bcmap', '/assets/pdfjs/cmaps/UniKS-UTF16-H.bcmap', '/assets/pdfjs/standard_fonts/FoxitFixedBoldItalic.pfb', '/assets/pdfjs/cmaps/Ext-V.bcmap', '/assets/pdfjs/cmaps/Add-RKSJ-V.bcmap', '/assets/pdfjs/wasm/quickjs-eval.wasm', '/assets/pdfjs/cmaps/UniJIS-UCS2-H.bcmap', '/assets/pdfjs/standard_fonts/FoxitSerif.pfb', '/assets/pdfjs/cmaps/UniJISX02132004-UTF32-V.bcmap', '/assets/pdfjs/cmaps/GB-V.bcmap', '/assets/pdfjs/cmaps/Adobe-CNS1-3.bcmap', '/assets/pdfjs/cmaps/UniGB-UCS2-V.bcmap', '/assets/pdfjs/cmaps/Adobe-GB1-UCS2.bcmap', '/assets/pdfjs/cmaps/UniGB-UTF32-V.bcmap', '/assets/pdfjs/cmaps/UniJISPro-UCS2-HW-V.bcmap', '/assets/pdfjs/cmaps/78-RKSJ-H.bcmap', '/assets/pdfjs/cmaps/78-EUC-V.bcmap'})
ROUND3_RESERVED_PREFIXES = ("/assets/books/", "/assets/book-covers/", "/assets/brand/", "/assets/pdfjs/", "/assets/ocr/")


def _pdf_range(values, size):
    """Return one inclusive byte interval; reject ambiguous/unbounded input."""
    if len(values) != 1 or len(values[0]) > 128:
        raise ValueError("Invalid range")
    match = re.fullmatch(r"bytes=([0-9]{0,20})-([0-9]{0,20})", values[0])
    if not match or not any(match.groups()) or size == 0:
        raise ValueError("Invalid range")
    first, last = match.groups()
    if not first:
        suffix = int(last)
        if suffix == 0:
            raise ValueError("Invalid range")
        return max(0, size - suffix), size - 1
    start = int(first)
    end = min(int(last), size - 1) if last else size - 1
    if start >= size or end < start:
        raise ValueError("Invalid range")
    return start, end


HASHED_ASSET_NAME = re.compile(r"\.[0-9a-fA-F]{8,64}\.")

# Temporary exceptions for the existing CDN/Babel build; tighten after a verified
# precompile rather than breaking translation or the current application.
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'", "base-uri 'self'", "object-src 'none'",
    "frame-ancestors 'none'", "form-action 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://unpkg.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://translate.google.com https://translate.googleapis.com https://www.gstatic.com https://www.youtube.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://translate.googleapis.com https://www.gstatic.com",
    "font-src 'self' https://fonts.gstatic.com data:",
    "img-src 'self' data: https://i.ytimg.com https://img.youtube.com https://translate.google.com https://translate.googleapis.com https://www.google.com https://www.gstatic.com https://*.googleusercontent.com",
    "connect-src 'self' https://translate.google.com https://translate.googleapis.com https://www.youtube.com https://cdnjs.cloudflare.com https://unpkg.com",
    "worker-src 'self' blob: https://cdnjs.cloudflare.com",
    "frame-src https://www.youtube.com https://www.youtube-nocookie.com https://translate.google.com",
    "media-src 'self' blob:",
])
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Permissions-Policy": 'camera=(), geolocation=(), microphone=(self), fullscreen=(self "https://www.youtube.com")',
}
LOGGER = logging.getLogger("maqam")


def _valid_text(value, maximum, *, allow_empty=False):
    return (isinstance(value, str) and len(value) <= maximum
            and (allow_empty or bool(value.strip()))
            and not any(ord(char) == 0 or 0xD800 <= ord(char) <= 0xDFFF for char in value))


def _uuid_string(value):
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        return str(uuid.UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def _identity(value):
    if not isinstance(value, str):
        return False
    prefix, separator, identifier = value.partition("_")
    return bool(separator and prefix in {"visitor", "student"} and _uuid_string(identifier))


def _authority(value, scheme):
    """Validate an authority, without trusting client-forwarded headers."""
    if not isinstance(value, str) or not value or len(value) > 255:
        raise ValueError("Invalid authority")
    if any(char.isspace() or ord(char) < 33 for char in value) or any(char in value for char in "@/\\?#,%"):
        raise ValueError("Invalid authority")
    parsed = urllib.parse.urlsplit(scheme + "://" + value)
    hostname = parsed.hostname
    if not hostname or parsed.username or parsed.password:
        raise ValueError("Invalid authority")
    if ":" in hostname:
        ipaddress.IPv6Address(hostname)
        hostname = "[" + hostname.lower() + "]"
    elif not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,251}[a-zA-Z0-9])?", hostname):
        raise ValueError("Invalid authority")
    port = parsed.port
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid authority")
    default_port = 443 if scheme == "https" else 80
    return hostname.lower() + (":" + str(port) if port is not None and port != default_port else "")


def _origin(value):
    if not isinstance(value, str) or any(char.isspace() for char in value):
        raise ValueError("Invalid origin")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Invalid origin")
    return parsed.scheme + "://" + _authority(parsed.netloc, parsed.scheme)


def _provider_endpoint():
    parsed = urllib.parse.urlsplit(DIFY_API_URL.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("Invalid provider configuration")
    _authority(parsed.netloc, "https")
    if any(part in {".", ".."} for part in parsed.path.split("/")) or "\\" in parsed.path:
        raise ValueError("Invalid provider configuration")
    return urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path.rstrip("/") + "/chat-messages", "", ""))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON property")
        result[key] = value
    return result


def _bad_json_constant(_value):
    raise ValueError("Invalid JSON constant")


def _parse_json(data):
    return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_bad_json_constant)


def _inputs(value):
    if not isinstance(value, dict) or len(value) > 20:
        return False
    for key, item in value.items():
        if not _valid_text(key, 64):
            return False
        if isinstance(item, str):
            if not _valid_text(item, 2_000, allow_empty=True):
                return False
        elif item is not None and not isinstance(item, (bool, int, float)):
            return False
        elif isinstance(item, (int, float)) and (abs(item) > 10 ** 15 or not math.isfinite(item)):
            return False
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8")) <= 4_096


def _citation_url(value):
    if not _valid_text(value, 2_048) or any(char.isspace() for char in value):
        return None
    try:
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            return None
        _authority(parsed.netloc, parsed.scheme)
    except ValueError:
        return None
    return value


def _citations(response):
    metadata = response.get("metadata")
    resources = metadata.get("retriever_resources") if isinstance(metadata, dict) else None
    if not isinstance(resources, list):
        return []
    sources, seen = [], set()
    for resource in resources[:40]:
        if not isinstance(resource, dict):
            continue
        title = resource.get("document_name")
        if not _valid_text(title, 200):
            continue
        title = title.strip()
        entry = {"title": title}
        link = _citation_url(resource.get("url"))
        if link:
            entry["url"] = link
        identity = (title, link)
        if identity not in seen:
            sources.append(entry)
            seen.add(identity)
        if len(sources) == 20:
            break
    return sources


class RejectProviderRedirects(urllib.request.HTTPRedirectHandler):
    """Never forward an Authorization header through provider redirects."""

    def redirect_request(self, *_args, **_kwargs):
        return None


class RateLimiter:
    def __init__(self):
        self._entries = OrderedDict()
        self._lock = threading.Lock()

    def admit(self, identity):
        now = time.monotonic()
        with self._lock:
            timestamps = self._entries.pop(identity, deque())
            while timestamps and timestamps[0] <= now - RATE_LIMIT_WINDOW_SECONDS:
                timestamps.popleft()
            if len(timestamps) >= RATE_LIMIT_COUNT:
                self._entries[identity] = timestamps
                return False, max(1, math.ceil(RATE_LIMIT_WINDOW_SECONDS - (now - timestamps[0])))
            timestamps.append(now)
            self._entries[identity] = timestamps
            while len(self._entries) > MAX_RATE_IDENTITIES:
                self._entries.popitem(last=False)
        return True, 0


def _provider_configured():
    key = DIFY_API_KEY
    try:
        _provider_endpoint()
        return isinstance(key, str) and 0 < len(key) <= 512 and all(33 <= ord(c) <= 126 for c in key)
    except ValueError:
        return False


def _provider_json(path, *, data=None, content_type=None):
    # Only literal caller-owned sibling paths; no request URL is ever accepted.
    if path not in {"parameters", "files/upload"}:
        raise ValueError("Invalid provider operation")
    endpoint = _provider_endpoint().removesuffix("chat-messages") + path
    headers = {"Authorization": "Bearer " + DIFY_API_KEY, "Accept": "application/json"}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST" if data is not None else "GET")
    opener = urllib.request.build_opener(RejectProviderRedirects())
    with opener.open(request, timeout=8) as response:
        if response.getcode() not in {200, 201}:
            raise ValueError("Provider status")
        deadline = time.monotonic() + 8
        chunks, size = [], 0
        while size <= MAX_UPSTREAM_BYTES:
            if time.monotonic() >= deadline:
                raise TimeoutError("Provider deadline")
            chunk = response.read1(min(65536, MAX_UPSTREAM_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > MAX_UPSTREAM_BYTES:
            raise ValueError("Provider size")
        result = _parse_json(b"".join(chunks))
        if not isinstance(result, dict):
            raise ValueError("Provider schema")
        return result


class VisionState:
    """Transient references only: no image bytes or publication on local storage."""
    def __init__(self):
        self.lock = threading.Lock()
        self.fetch_lock = threading.Lock()
        self.capability = None
        self.uploads = OrderedDict()

    def save_capability(self, enabled):
        with self.lock:
            self.capability = (time.monotonic() + 60, bool(enabled))

    def vision(self):
        with self.fetch_lock:
            with self.lock:
                cached = self.capability
            if cached and cached[0] > time.monotonic():
                return cached[1]
            try:
                result = _provider_json("parameters")
                upload = result.get("file_upload")
                image = upload.get("image") if isinstance(upload, dict) else None
                enabled = ((isinstance(image, dict) and image.get("enabled") is True)
                    or (isinstance(upload, dict) and upload.get("enabled") is True
                        and isinstance(upload.get("allowed_file_types"), list)
                        and "image" in upload["allowed_file_types"]
                        and isinstance(upload.get("allowed_file_upload_methods"), list)
                        and "local_file" in upload["allowed_file_upload_methods"]))
            except urllib.error.HTTPError as error:
                error.close()
                enabled = False
            except (ValueError, TypeError, UnicodeError, OSError, RecursionError, urllib.error.URLError):
                enabled = False
            self.save_capability(enabled)
            return enabled

    def issue(self, owner, provider_id):
        now = time.monotonic()
        local_id = str(uuid.uuid4())
        with self.lock:
            for key, entry in list(self.uploads.items()):
                if entry[0] <= now:
                    del self.uploads[key]
            owned = [key for key, entry in self.uploads.items() if entry[1] == owner]
            for key in owned[:-7]:
                del self.uploads[key]
            self.uploads[local_id] = (now + 900, owner, provider_id)
            while len(self.uploads) > 512:
                self.uploads.popitem(last=False)
        return local_id

    def owned(self, local_id, owner):
        with self.lock:
            entry = self.uploads.get(local_id)
            if entry and entry[0] > time.monotonic() and entry[1] == owner:
                return entry[2]
            return None


def _image_dimensions(raw, mime):
    """Parse container headers without decompressing attacker-controlled pixels."""
    if mime == "image/png" and raw.startswith(b"\x89PNG\r\n\x1a\n"):
        offset, dimensions, ended, image_data = 8, None, False, False
        while offset + 12 <= len(raw):
            size = int.from_bytes(raw[offset:offset+4], "big")
            kind = raw[offset+4:offset+8]
            end = offset + 12 + size
            if end > len(raw) or zlib.crc32(raw[offset+4:end-4]) & 0xffffffff != int.from_bytes(raw[end-4:end], "big"):
                raise ValueError("PNG chunk")
            if dimensions is None:
                if kind != b"IHDR" or size != 13:
                    raise ValueError("PNG header")
                dimensions = struct.unpack(">II", raw[offset+8:offset+16])
            elif kind == b"IHDR":
                raise ValueError("PNG duplicate header")
            if kind in {b"acTL", b"fcTL", b"fdAT"}:
                raise ValueError("Animated image unsupported")
            if kind == b"IDAT":
                image_data = True
            if kind == b"IEND":
                ended = size == 0 and end == len(raw)
                break
            offset = end
        if ended and image_data:
            return dimensions
    elif mime == "image/jpeg" and raw.startswith(b"\xff\xd8") and raw.endswith(b"\xff\xd9"):
        offset, dimensions = 2, None
        while offset + 4 <= len(raw):
            if raw[offset] != 255:
                raise ValueError("JPEG marker")
            while offset < len(raw) and raw[offset] == 255:
                offset += 1
            marker = raw[offset]
            offset += 1
            if marker == 0xDA:
                if dimensions:
                    return dimensions
                break
            size = int.from_bytes(raw[offset:offset+2], "big")
            if size < 2 or offset + size > len(raw):
                raise ValueError("JPEG segment")
            if marker in {0xC0, 0xC1, 0xC2}:
                if size < 8:
                    raise ValueError("JPEG frame")
                height, width = struct.unpack(">HH", raw[offset+3:offset+7])
                dimensions = (width, height)
            offset += size
    elif mime == "image/webp" and len(raw) >= 30 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP" and int.from_bytes(raw[4:8], "little") + 8 == len(raw):
        offset, canvas, dimensions = 12, None, None
        while offset + 8 <= len(raw):
            kind, size = raw[offset:offset+4], int.from_bytes(raw[offset+4:offset+8], "little")
            data = raw[offset+8:offset+8+size]
            end = offset + 8 + size + (size % 2)
            if end > len(raw):
                raise ValueError("WebP chunk")
            if kind in {b"ANIM", b"ANMF"}:
                raise ValueError("Animated image unsupported")
            if kind == b"VP8X":
                if canvas or offset != 12 or size != 10 or data[0] & 2:
                    raise ValueError("WebP canvas")
                canvas = (int.from_bytes(data[4:7], "little") + 1, int.from_bytes(data[7:10], "little") + 1)
            elif kind in {b"VP8 ", b"VP8L"}:
                if dimensions:
                    raise ValueError("WebP duplicate frame")
                if kind == b"VP8 " and size >= 10 and data[3:6] == b"\x9d\x01\x2a":
                    dimensions = (int.from_bytes(data[6:8], "little") & 0x3fff, int.from_bytes(data[8:10], "little") & 0x3fff)
                elif kind == b"VP8L" and size >= 5 and data[0] == 0x2f:
                    bits = int.from_bytes(data[1:5], "little")
                    dimensions = ((bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1)
                else:
                    raise ValueError("WebP frame")
            offset = end
        if offset == len(raw) and dimensions and (canvas is None or canvas == dimensions):
            return dimensions
    raise ValueError("Invalid image container")


def _validated_image(data):
    if not isinstance(data, dict) or set(data) != {"user", "name", "type", "data"} or not _identity(data.get("user")):
        raise ValueError("Invalid upload")
    name, mime, encoded = data["name"], data["type"], data["data"]
    extensions = {"image/png": {"png"}, "image/jpeg": {"jpg", "jpeg"}, "image/webp": {"webp"}}
    if (not isinstance(name, str) or not re.fullmatch(r"[\w -]{1,100}\.(?:png|jpg|jpeg|webp)", name, re.ASCII | re.IGNORECASE)
            or mime not in extensions or name.rsplit(".", 1)[-1].lower() not in extensions[mime]
            or not isinstance(encoded, (str, bytes))):
        raise ValueError("Invalid upload metadata")
    raw = encoded if isinstance(encoded, bytes) else base64.b64decode(encoded, validate=True)
    if len(raw) > MAX_IMAGE_BYTES:
        raise OverflowError("Image size")
    width, height = _image_dimensions(raw, mime)
    if not (1 <= width <= 4096 and 1 <= height <= 4096):
        raise ValueError("Image dimensions")
    return data["user"], mime, raw


def _multipart_upload(body, content_type):
    if len(content_type) > 256 or "\r" in content_type or "\n" in content_type:
        raise ValueError("Multipart header")
    message = email.parser.BytesParser(policy=email.policy.default).parsebytes(("Content-Type: " + content_type + "\r\nMIME-Version: 1.0\r\n\r\n").encode("ascii") + body)
    if not message.is_multipart() or message.defects:
        raise ValueError("Multipart framing")
    parts = list(message.iter_parts())
    if len(parts) != 2:
        raise ValueError("Multipart fields")
    values = {}
    for part in parts:
        if part.defects or part.is_multipart() or part.get_content_disposition() != "form-data" or len(list(part.items())) > 2:
            raise ValueError("Multipart part")
        field = part.get_param("name", header="content-disposition")
        if field not in {"user", "file"} or field in values:
            raise ValueError("Multipart field")
        values[field] = part
    if set(values) != {"user", "file"}:
        raise ValueError("Multipart fields")
    user, file = values["user"], values["file"]
    if user.get_filename() or file.get("Content-Transfer-Encoding"):
        raise ValueError("Multipart encoding")
    return {"user": user.get_payload(decode=True).decode("utf-8"), "name": file.get_filename(), "type": file.get_content_type(), "data": file.get_payload(decode=True)}


class TranslationState:
    """Bounded process-local cache, throttles and provider cooldown."""
    def __init__(self):
        self.lock = threading.Lock()
        self.cache = OrderedDict()
        self.ips = OrderedDict()
        self.global_times = deque()
        self.cooldown = 0

    def admit(self, identity):
        now = time.monotonic()
        with self.lock:
            if self.cooldown > now:
                return False, max(1, math.ceil(self.cooldown - now))
            times = self.ips.pop(identity, deque())
            for queue in (times, self.global_times):
                while queue and queue[0] <= now - 60:
                    queue.popleft()
            self.ips[identity] = times
            while len(self.ips) > 4096:
                self.ips.popitem(last=False)
            if len(times) >= 60 or len(self.global_times) >= 60:
                return False, 60
            times.append(now)
            self.global_times.append(now)
            return True, 0

    def cached(self, key):
        with self.lock:
            entry = self.cache.get(key)
            if entry and entry[0] > time.monotonic():
                self.cache.move_to_end(key)
                return entry[1]
            self.cache.pop(key, None)
            return None

    def save(self, key, value):
        with self.lock:
            self.cache[key] = (time.monotonic() + 3600, value)
            while len(self.cache) > 256:
                self.cache.popitem(last=False)


def _translation_targets():
    # Repository-owned canonical metadata; never a request-controlled pathname.
    rows = _parse_json((BASE_DIR / "data" / "languages.json").read_bytes())
    codes = [row["code"] for row in rows if isinstance(row, dict) and isinstance(row.get("code"), str)]
    blocked = {"ber", "bat", "rhg", "bal", "bci", "tum", "tiv", "dyo", "lmo", "mad", "jw", "iw", "gd"}
    return frozenset(code for code in codes if code not in blocked and re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z]{2,4})?", code))


class MaqamHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True
    request_queue_size = 32

    def process_request(self, request, client_address):
        if not self.worker_slots.acquire(blocking=False):
            body = json.dumps({"success": False, "error": "الخدمة مشغولة الآن. يرجى المحاولة لاحقاً."}, ensure_ascii=False).encode("utf-8")
            fields = {**SECURITY_HEADERS, "Content-Type": "application/json; charset=utf-8", "Content-Length": str(len(body)), "Cache-Control": "no-store", "Connection": "close", "Retry-After": "1"}
            wire = ("HTTP/1.0 503 Service Unavailable\r\n" + "".join(key + ": " + value + "\r\n" for key, value in fields.items()) + "\r\n").encode("ascii") + body
            try:
                request.settimeout(1)
                request.sendall(wire)
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.worker_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.worker_slots.release()

    def handle_error(self, _request, _client_address):
        LOGGER.warning("Request handling failed")


class MaqamProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "Maqam"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(CLIENT_TIMEOUT_SECONDS)

    def log_message(self, _format, *_args):
        # Do not log targets, bodies, provider errors or credential substrings.
        pass

    def end_headers(self):
        self.send_header("Cache-Control", getattr(self, "cache_policy", "no-store"))
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        if getattr(self, "allowed_origin", None):
            self.send_header("Access-Control-Allow-Origin", self.allowed_origin)
            self.send_header("Vary", "Origin")
        super().end_headers()

    def _json(self, status, value, *, head=False, extra_headers=None):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.cache_policy = "no-store"
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if not head and self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                pass

    def _error(self, status, *, extra_headers=None):
        messages = {
            400: "تعذر قبول الطلب. يرجى التحقق من البيانات والمحاولة مجدداً.",
            403: "هذا الطلب غير مسموح من الصفحة الحالية.",
            404: "المسار غير موجود.",
            405: "طريقة الطلب غير مدعومة.",
            408: "انتهت مهلة استقبال الطلب. يرجى المحاولة مجدداً.",
            411: "تعذر قبول الطلب. يرجى المحاولة مجدداً.",
            413: "حجم الطلب أكبر من المسموح. يرجى اختصار النص.",
            415: "صيغة الطلب غير مدعومة.",
            416: "نطاق الملف المطلوب غير صالح.",
            429: "تم إرسال طلبات كثيرة. يرجى الانتظار قليلاً والمحاولة مجدداً.",
            500: "تعذر إتمام الطلب الآن. يرجى المحاولة لاحقاً.",
            502: "تعذر الحصول على إجابة الآن. يرجى المحاولة مجدداً.",
            503: "خدمة المحادثة غير متاحة الآن. يرجى المحاولة لاحقاً.",
            504: "استغرقت الإجابة وقتاً أطول من المتاح. يرجى المحاولة مجدداً.",
        }
        self._json(status, {"success": False, "error": messages.get(status, messages[400])}, extra_headers=extra_headers)

    def send_error(self, code, message=None, explain=None):
        self._error(code)

    def _begin(self):
        self.allowed_origin = None
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1:
            self._error(400)
            return False
        public_origin = self.server.public_origin
        scheme = urllib.parse.urlsplit(public_origin).scheme if public_origin else "http"
        try:
            authority = _authority(hosts[0], scheme)
        except ValueError:
            self._error(400)
            return False
        if authority not in self.server.allowed_authorities:
            self._error(403)
            return False
        origins = self.headers.get_all("Origin", [])
        if len(origins) > 1:
            self._error(403)
            return False
        if origins:
            try:
                given = _origin(origins[0])
            except ValueError:
                self._error(403)
                return False
            expected = public_origin or scheme + "://" + authority
            if given != expected:
                self._error(403)
                return False
            self.allowed_origin = expected
        return True

    def _path(self):
        if not self.path.startswith("/") or self.path.startswith("//"):
            return None
        try:
            path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path, encoding="utf-8", errors="strict")
        except (ValueError, UnicodeError):
            return None
        if any(ord(char) < 32 or ord(char) == 127 for char in path) or any(char in path for char in "\\:%?#"):
            return None
        # Path must retain the same segments on POSIX and Windows filesystems.
        if "//" in path or any(part.endswith((".", " ")) for part in path.split("/") if part):
            return None
        if any(part.startswith(".") for part in path.split("/") if part):
            return None
        return path

    def _serve(self, *, head=False):
        if not self._begin():
            return
        path = self._path()
        if path == "/api/health":
            try:
                app = (self.server.base_dir / APP_FILE).resolve(strict=True)
                ready = app.is_file() and app.is_relative_to(self.server.base_dir)
            except OSError:
                ready = False
            self._json(200 if ready else 503, {"status": "ok" if ready else "unavailable"}, head=head)
            return
        if path == "/api/capabilities":
            admitted, retry = self.server.capability_limiter.admit(self.client_address[0])
            if not admitted:
                self._error(429, extra_headers={"Retry-After": str(retry)})
                return
            configured = _provider_configured()
            self._json(200, {"configured": configured, "vision": configured and self.server.vision_state.vision()}, head=head)
            return
        root = self.server.base_dir
        if path in {"/", "/" + APP_FILE}:
            candidate, asset = root / APP_FILE, False
        elif path in (ROUND3_PUBLIC_PATHS | ROUND4_PUBLIC_PATHS):
            candidate, asset = root / path.lstrip("/"), True
        elif (path and path.startswith("/assets/")
              and not path.lower().startswith(ROUND3_RESERVED_PREFIXES)
              and Path(path).suffix.lower() in PUBLIC_ASSET_EXTENSIONS):
            candidate, asset = root / path.lstrip("/"), True
        else:
            self._error(404)
            return
        try:
            # Reject symlink components even when their destination remains inside root.
            if any(part.is_symlink() for part in (candidate, *candidate.parents) if part != root and part.is_relative_to(root)):
                self._error(404)
                return
            resolved = candidate.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                self._error(404)
                return
            if asset and path not in (ROUND3_PUBLIC_PATHS | ROUND4_PUBLIC_PATHS) and (not resolved.is_relative_to(root / "assets") or resolved.suffix.lower() not in PUBLIC_ASSET_EXTENSIONS):
                self._error(404)
                return
            if not asset and resolved.name != APP_FILE:
                self._error(404)
                return
            source = resolved.open("rb")
        except (OSError, ValueError):
            self._error(404)
            return
        try:
            with source:
                self.cache_policy = ("public, max-age=31536000, immutable" if HASHED_ASSET_NAME.search(resolved.name) else "public, max-age=3600, must-revalidate") if asset else "no-cache"
                size = os.fstat(source.fileno()).st_size
                is_pdf = path in (ROUND3_PUBLIC_PATHS | ROUND4_PUBLIC_PATHS) and resolved.suffix == ".pdf"
                ranges = self.headers.get_all("Range", []) if is_pdf else []
                start, end = 0, size - 1
                if ranges:
                    try:
                        start, end = _pdf_range(ranges, size)
                    except ValueError:
                        self._error(416, extra_headers={"Content-Range": f"bytes */{size}", "Accept-Ranges": "bytes"})
                        return
                self.send_response(206 if ranges else 200)
                if is_pdf:
                    self.send_header("Accept-Ranges", "bytes")
                if ranges:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
                if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
                    content_type += "; charset=utf-8"
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(end - start + 1))
                self.end_headers()
                if not head:
                    source.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        block = source.read(min(65_536, remaining))
                        if not block:
                            break
                        self.wfile.write(block)
                        remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def do_GET(self):
        self._serve()

    def do_HEAD(self):
        self._serve(head=True)

    def do_OPTIONS(self):
        if not self._begin():
            return
        if self._path() not in {"/api/chat", "/api/translate", "/api/upload"}:
            self._error(404)
            return
        if self.headers.get("Access-Control-Request-Method", "POST").upper() != "POST":
            self._error(405)
            return
        requested = {item.strip().lower() for item in self.headers.get("Access-Control-Request-Headers", "").split(",") if item.strip()}
        if not requested.issubset({"content-type"}):
            self._error(403)
            return
        self.cache_policy = "no-store"
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if not self._begin():
            return
        if self._path() not in {"/api/chat", "/api/translate", "/api/upload"}:
            self._error(404)
            return
        upload = self._path() == "/api/upload"
        if upload and not self.allowed_origin:
            self._error(403)
            return
        translation = self._path() == "/api/translate"
        maximum = MAX_UPLOAD_BODY_BYTES if upload else MAX_BODY_BYTES
        limiter = self.server.translation_state if translation else self.server.rate_limiter
        admitted, retry_after = limiter.admit(self.client_address[0])
        if not admitted:
            self._error(429, extra_headers={"Retry-After": str(retry_after)})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1 or not re.fullmatch(r"[0-9]+", lengths[0]):
            self._error(400 if lengths else 411)
            return
        normalized_length = lengths[0].lstrip("0") or "0"
        if len(normalized_length) > len(str(maximum)):
            self._error(413)
            return
        length = int(normalized_length)
        if length > maximum:
            self._error(413)
            return
        if length <= 0:
            self._error(400)
            return
        multipart = upload and self.headers.get_content_type() == "multipart/form-data"
        if not multipart and (self.headers.get_content_type() != "application/json" or self.headers.get_content_charset("utf-8").lower() not in {"utf-8", "utf8"}):
            self._error(415)
            return
        try:
            deadline = time.monotonic() + CLIENT_TIMEOUT_SECONDS
            chunks, remaining = [], length
            while remaining:
                budget = deadline - time.monotonic()
                if budget <= 0:
                    raise TimeoutError("Body deadline")
                self.connection.settimeout(budget)
                chunk = self.rfile.read1(remaining)
                if time.monotonic() >= deadline:
                    raise TimeoutError("Body deadline")
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            body = b"".join(chunks)
            if len(body) != length:
                raise ValueError("Incomplete body")
            data = _multipart_upload(body, self.headers.get("Content-Type", "")) if multipart else _parse_json(body)
            if upload:
                owner, mime, raw = _validated_image(data)
                self.handle_image_upload(owner, mime, raw)
                return
            if translation:
                if (not isinstance(data, dict) or set(data) != {"text", "target", "source"}
                        or data["source"] != "ar" or not isinstance(data["target"], str)
                        or data["target"] not in self.server.translation_targets
                        or not _valid_text(data["text"], 4000)
                        or any((ord(char) < 32 and char not in "\n\t") or ord(char) == 127 for char in data["text"])):
                    raise ValueError("Invalid translation")
                self.handle_translation(data["text"], data["target"])
                return
            if not isinstance(data, dict) or not set(data).issubset({"query", "user", "conversation_id", "inputs", "files"}):
                raise ValueError("Invalid payload")
            query, identity, conversation = data.get("query"), data.get("user"), data.get("conversation_id", "")
            inputs = data.get("inputs", {})
            if not _valid_text(query, MAX_QUERY_CHARS) or not _identity(identity) or not isinstance(conversation, str) or (conversation and not _uuid_string(conversation)) or not _inputs(inputs):
                raise ValueError("Invalid payload")
            files = None
            if "files" in data:
                references = data["files"]
                if not isinstance(references, list) or not 1 <= len(references) <= 3 or len(set(item for item in references if isinstance(item, str))) != len(references):
                    raise ValueError("Invalid attachments")
                files = []
                for local_id in references:
                    if not _uuid_string(local_id):
                        raise ValueError("Invalid attachment")
                    provider_id = self.server.vision_state.owned(local_id, identity)
                    if provider_id is None:
                        raise ValueError("Unowned attachment")
                    files.append({"type": "image", "transfer_method": "local_file", "upload_file_id": provider_id})
        except OverflowError:
            self._error(413)
            return
        except (socket.timeout, TimeoutError):
            self._error(408)
            return
        except (ValueError, UnicodeError, TypeError, RecursionError):
            self._error(400)
            return
        self.handle_dify_chat(query.strip(), identity, conversation, inputs, files)

    def handle_translation(self, text, target):
        state = self.server.translation_state
        key = (text, target)
        cached = state.cached(key)
        if cached is not None:
            self._json(200, {"text": cached, "target": target})
            return
        query = urllib.parse.urlencode({"client": "gtx", "sl": "ar", "tl": target, "dt": "t", "q": text})
        request = urllib.request.Request("https://translate.googleapis.com/translate_a/single?" + query, headers={"Accept": "application/json"})
        opener = urllib.request.build_opener(RejectProviderRedirects())
        try:
            with opener.open(request, timeout=8) as response:
                if response.getcode() != 200:
                    raise ValueError("Provider status")
                deadline = time.monotonic() + 8
                chunks, size = [], 0
                while size <= 65536:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Provider deadline")
                    chunk = response.read1(min(8192, 65537 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                raw = b"".join(chunks)
                if len(raw) > 65536:
                    raise ValueError("Provider size")
                result = _parse_json(raw)
            if not isinstance(result, list) or not result or not isinstance(result[0], list) or not 1 <= len(result[0]) <= 4000:
                raise ValueError("Provider format")
            parts = []
            for row in result[0]:
                if not isinstance(row, list) or not row or not _valid_text(row[0], 16000):
                    raise ValueError("Provider translation")
                parts.append(row[0])
            translated = "".join(parts)
            if not _valid_text(translated, 16000):
                raise ValueError("Provider translation")
            state.save(key, translated)
            self._json(200, {"text": translated, "target": target})
        except urllib.error.HTTPError as error:
            status = error.code
            error.close()
            if status == 429:
                with state.lock:
                    state.cooldown = time.monotonic() + 60
                self._error(429, extra_headers={"Retry-After": "60"})
            else:
                self._error(502)
        except (urllib.error.URLError, ValueError, TypeError, UnicodeError, OSError, RecursionError):
            self._error(502)

    def handle_image_upload(self, owner, mime, raw):
        if not _provider_configured() or not self.server.vision_state.vision():
            self._error(503)
            return
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[mime]
        boundary = "maqam-" + uuid.uuid4().hex
        # Never interpolate the user-supplied filename into provider headers.
        prefix = ("--" + boundary + '\r\nContent-Disposition: form-data; name="user"\r\n\r\n' + owner
            + "\r\n--" + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="notes.' + extension
            + '"\r\nContent-Type: ' + mime + "\r\n\r\n").encode("ascii")
        body = prefix + raw + ("\r\n--" + boundary + "--\r\n").encode("ascii")
        try:
            result = _provider_json("files/upload", data=body, content_type="multipart/form-data; boundary=" + boundary)
            if not _uuid_string(result.get("id")):
                raise ValueError("Provider upload id")
            local_id = self.server.vision_state.issue(owner, result["id"])
            self._json(200, {"success": True, "upload_id": local_id, "expires_in": 900})
        except (socket.timeout, TimeoutError):
            self._error(504)
        except urllib.error.HTTPError as error:
            error.close()
            self._error(503 if error.code == 429 else 502)
        except urllib.error.URLError as error:
            self._error(504 if isinstance(error.reason, (socket.timeout, TimeoutError)) else 502)
        except (ValueError, TypeError, UnicodeError, OSError, RecursionError):
            self._error(502)

    def handle_dify_chat(self, query, identity, conversation, inputs, files=None):
        key = DIFY_API_KEY
        if not isinstance(key, str) or not key or len(key) > 512 or any(ord(char) < 33 or ord(char) > 126 for char in key):
            self._error(503)
            return
        try:
            endpoint = _provider_endpoint()
        except ValueError:
            self._error(503)
            return
        payload = {"query": query, "user": identity, "conversation_id": conversation, "inputs": inputs, "response_mode": "blocking"}
        if files:
            payload["files"] = files
        request = urllib.request.Request(endpoint, data=json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"), headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        opener = urllib.request.build_opener(RejectProviderRedirects())
        try:
            with opener.open(request, timeout=UPSTREAM_TIMEOUT_SECONDS) as response:
                if response.getcode() != 200:
                    raise ValueError("Invalid provider status")
                raw = response.read(MAX_UPSTREAM_BYTES + 1)
                if len(raw) > MAX_UPSTREAM_BYTES:
                    raise ValueError("Provider response too large")
                result = _parse_json(raw)
            if not isinstance(result, dict) or not _valid_text(result.get("answer"), MAX_UPSTREAM_BYTES):
                raise ValueError("Invalid provider response")
            new_conversation = result.get("conversation_id", conversation)
            if not isinstance(new_conversation, str) or (new_conversation and not _uuid_string(new_conversation)):
                raise ValueError("Invalid conversation")
            message_id = result.get("message_id", result.get("id", ""))
            if not isinstance(message_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{0,128}", message_id):
                message_id = ""
            self._json(200, {"success": True, "answer": result["answer"], "conversation_id": new_conversation, "message_id": message_id, "sources": _citations(result)})
        except (socket.timeout, TimeoutError):
            self._error(504)
        except urllib.error.HTTPError as error:
            error.close()
            self._error(503 if error.code == 429 else 502)
        except urllib.error.URLError as error:
            self._error(504 if isinstance(error.reason, (socket.timeout, TimeoutError)) else 502)
        except (ValueError, TypeError, UnicodeError, OSError, RecursionError):
            self._error(502)


def create_server(host, port, base_dir=None):
    """Create one listener with no directory listing or implicit source serving."""
    root = Path(base_dir if base_dir is not None else BASE_DIR).resolve()
    origin_value = os.environ.get("PUBLIC_ORIGIN") or os.environ.get("RENDER_EXTERNAL_URL")
    public_origin = _origin(origin_value) if origin_value else None
    server = MaqamHTTPServer((host, port), MaqamProxyHandler)
    server.base_dir = root
    server.public_origin = public_origin
    actual_port = server.server_address[1]
    local_hosts = {"localhost", "127.0.0.1"}
    if host not in {"", "0.0.0.0"}:
        local_hosts.add(host)
    scheme = urllib.parse.urlsplit(public_origin).scheme if public_origin else "http"
    server.allowed_authorities = {_authority(value + ":" + str(actual_port), scheme) for value in local_hosts}
    if public_origin:
        server.allowed_authorities.add(urllib.parse.urlsplit(public_origin).netloc)
    server.rate_limiter = RateLimiter()
    server.capability_limiter = RateLimiter()
    server.vision_state = VisionState()
    server.translation_state = TranslationState()
    server.translation_targets = _translation_targets()
    server.worker_slots = threading.BoundedSemaphore(MAX_REQUEST_WORKERS)
    return server


def serve_on_port(port):
    """Compatibility for the existing Render command during this rollout."""
    with create_server("0.0.0.0", int(port)) as httpd:
        LOGGER.info("Maqam server ready")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    try:
        port = int(os.environ.get("PORT", "5000"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("PORT must be an integer between 1 and 65535") from None
    serve_on_port(port)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
