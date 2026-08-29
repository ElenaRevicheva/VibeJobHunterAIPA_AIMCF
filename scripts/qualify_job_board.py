#!/usr/bin/env python3
"""
QUALIFY A JOB BOARD - evidence, not marketing copy (added 2026-08-29)

WHY
On 2026-08-29 two curated "AI builder" boards were considered for VJH. Their
marketing was indistinguishable; their data was not.

    metric                        ai-native-builder   agentic-engineering-jobs
    newest posting                     19 days                32 days
    median posting age                 24 days                65 days
    posted within 30 days           99/145 (68%)            0/400 (0%)
    past the board's OWN expiry         4.8%                  99.8%
    expired but self-flagged fresh          -                    137
    VERDICT                            QUALIFIED               REJECTED

The rejected one had the better website, the bigger listing count and a polished
public API. Nothing but the dates gave it away. So this script exists to make the
dates the deciding vote, every time, for every board.

USAGE

  Qualify a candidate before wiring it in:
      python scripts/qualify_job_board.py https://example-jobs.com

  Re-check the boards already wired into VJH (cron this weekly):
      python scripts/qualify_job_board.py --watch
      python scripts/qualify_job_board.py --watch --alert    # Telegram on failure

EXIT CODES:  0 = qualified   1 = rejected   2 = could not evaluate
"""

import argparse
import asyncio
import datetime as dt
import json
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aiohttp  # noqa: E402

UA = "VibeJobHunter/1.0 (+https://aideazz.xyz)"
SAMPLE = 60          # detail pages to sample; enough for a stable median
CONCURRENCY = 5

# ── Thresholds. Derived from the two boards measured on 2026-08-29, not invented.
#
# NOTE on why "% expired" is reported but is NOT a rejection criterion. The first
# version of this script failed ai-native-builder at 31% expired. That was the
# wrong test: a healthy board that never deletes anything accumulates a stale tail,
# and board_hygiene.py drops that tail at ingest. What actually distinguishes a
# living board from an abandoned one is whether it is STILL POSTING, and how much
# live supply is left once the dead listings are removed:
#
#     ai-native-builder   newest 19d   median 34d   ~69% live   ~238 live postings
#     agentic-eng-jobs    newest 32d   median 65d    ~0.2% live      ~3 live postings
#
# So: judge the living remainder, not the corpse count.
MAX_MEDIAN_AGE_DAYS = 45     # ai-native-builder measured 34; the reject measured 65
MAX_NEWEST_AGE_DAYS = 21     # a live board posts something inside three weeks
MIN_LIVE_PCT = 40.0          # share still unexpired and inside MAX_AGE
MIN_LIVE_POSTINGS = 50       # absolute floor: a board with 3 live roles is not a source
MIN_DATED_PCT = 60.0         # an undated board cannot be checked for ghosts at all
MAX_FLUFF_PCT = 10.0         # "talent pool" listings that name no opening

# Boards currently wired into VJH, re-checked by --watch.
WIRED_BOARDS = ["https://www.ai-native-builder.com"]

_LDJSON_RE = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
_ATS_RE = re.compile(
    r"greenhouse|lever\.co|ashbyhq|workable|teamtailor|zohorecruit|"
    r"smartrecruiters|recruitee|bamboohr|jobvite|myworkdayjobs|breezy|personio")
_FLUFF_RE = re.compile(
    r"talent\s*(pool|community|network|pipeline)|general\s*application|"
    r"expression\s+of\s+interest|future\s+opportunit|evergreen\s+req|"
    r"candidate\s*pool|speculative\s+application|join\s+our\s+talent", re.I)


def _date(v) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except Exception:
        return None


async def _get(session, url, timeout=20) -> Optional[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            return await r.text() if r.status == 200 else None
    except Exception:
        return None


async def _robots_allows(session, base: str) -> Tuple[bool, str]:
    """Read robots.txt and honour the User-agent:* block. We never impersonate a
    named AI crawler to obtain access a generic client is not granted."""
    txt = await _get(session, urljoin(base, "/robots.txt"))
    if txt is None:
        return True, "no robots.txt (default allow)"
    star, active = [], False
    for line in txt.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            active = (v == "*")
        elif active and k in ("allow", "disallow"):
            star.append((k, v))
    if any(k == "disallow" and v == "/" for k, v in star):
        return False, "robots.txt disallows / for User-agent: *"
    return True, "robots.txt allows generic crawlers"


async def _job_urls(session, base: str) -> List[str]:
    """Collect posting URLs from the declared sitemap(s)."""
    urls: List[str] = []
    seen_maps = set()
    queue = [urljoin(base, "/sitemap.xml")]
    robots = await _get(session, urljoin(base, "/robots.txt")) or ""
    queue += re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots)

    while queue and len(urls) < 4000:
        sm_url = queue.pop(0)
        if sm_url in seen_maps:
            continue
        seen_maps.add(sm_url)
        xml = await _get(session, sm_url, 30)
        if not xml:
            continue
        if "<sitemapindex" in xml:
            queue += re.findall(r"<loc>(.*?)</loc>", xml)[:20]
            continue
        for loc in re.findall(r"<loc>(.*?)</loc>", xml):
            if re.search(r"/(jobs?|positions?|roles?|careers?|vacanc\w*)/[^/]+$", loc):
                urls.append(loc)
    return urls


def _parse_posting(html: str, url: str) -> Optional[Dict]:
    for block in _LDJSON_RE.findall(html):
        try:
            d = json.loads(block)
        except Exception:
            continue
        for cand in (d if isinstance(d, list) else [d]):
            if isinstance(cand, dict) and cand.get("@type") == "JobPosting":
                org = cand.get("hiringOrganization") or {}
                return {
                    "title": cand.get("title") or "",
                    "company": (org.get("name") if isinstance(org, dict) else "") or "",
                    "posted": _date(cand.get("datePosted")),
                    "expires": _date(cand.get("validThrough")),
                    "ats": bool(_ATS_RE.search(html)),
                    "url": url,
                }
    return None


async def evaluate(base: str) -> Dict:
    base = base if base.startswith("http") else "https://" + base
    host = urlparse(base).netloc
    out: Dict = {"board": host, "errors": []}

    async with aiohttp.ClientSession(headers={"User-Agent": UA}) as s:
        ok, why = await _robots_allows(s, base)
        out["robots"] = why
        if not ok:
            out["errors"].append("robots.txt forbids generic crawling")
            return out

        urls = await _job_urls(s, base)
        out["listings_in_sitemap"] = len(urls)
        if len(urls) < 20:
            out["errors"].append(
                f"only {len(urls)} posting URLs discoverable in the sitemap")
            return out

        step = max(1, len(urls) // SAMPLE)
        sample = urls[::step][:SAMPLE]
        sem = asyncio.Semaphore(CONCURRENCY)

        async def one(u):
            async with sem:
                html = await _get(s, u)
                await asyncio.sleep(0.15)
            return _parse_posting(html, u) if html else None

        rows = [r for r in await asyncio.gather(*[one(u) for u in sample]) if r]

    out["sampled"] = len(sample)
    out["parsed"] = len(rows)
    if len(rows) < 10:
        out["errors"].append(
            f"only {len(rows)}/{len(sample)} pages exposed JobPosting structured data")
        return out

    today = dt.date.today()
    dated = [r for r in rows if r["posted"]]
    ages = sorted((today - r["posted"]).days for r in dated)

    out["structured_data_pct"] = round(len(rows) / len(sample) * 100, 1)
    out["dated_pct"] = round(len(dated) / len(rows) * 100, 1)
    out["newest_age_days"] = ages[0] if ages else None
    out["median_age_days"] = int(statistics.median(ages)) if ages else None
    out["within_30d_pct"] = round(
        sum(1 for a in ages if a <= 30) / len(ages) * 100, 1) if ages else 0.0
    exp = [r for r in rows if r["expires"] and r["expires"] < today]
    out["expired_pct"] = round(len(exp) / len(rows) * 100, 1)
    out["fluff_pct"] = round(
        sum(1 for r in rows if _FLUFF_RE.search(r["title"])) / len(rows) * 100, 1)
    out["direct_ats_pct"] = round(
        sum(1 for r in rows if r["ats"]) / len(rows) * 100, 1)

    # The living remainder: what survives the same hygiene gate the ingest applies.
    live = [r for r in rows
            if not (r["expires"] and r["expires"] < today)
            and not (r["posted"] and (today - r["posted"]).days > MAX_MEDIAN_AGE_DAYS)
            and not _FLUFF_RE.search(r["title"])]
    out["live_pct"] = round(len(live) / len(rows) * 100, 1)
    out["live_postings_est"] = int(out["listings_in_sitemap"] * len(live) / len(rows))

    # Yield against Elena's real career gate - the only relevance test that counts.
    # Import the module file directly: going through src.autonomous.__init__ drags in
    # the whole orchestrator (slow, and its emoji log lines crash cp1252 terminals).
    try:
        import importlib.util
        _p = Path(__file__).resolve().parents[1] / "src" / "autonomous" / "job_gate.py"
        _spec = importlib.util.spec_from_file_location("_vjh_job_gate", _p)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        passed = sum(1 for r in live if _mod.JobGate.passes({
            "title": r["title"], "company": r["company"],
            "location": "Remote", "description": r["title"]}))
        out["gate_pass_pct"] = round(passed / len(live) * 100, 1) if live else 0.0
    except Exception as e:  # never let the gate import sink a qualification run
        out["gate_pass_pct"] = None
        out["errors"].append(f"gate check skipped: {e}")

    fails = []
    if out["dated_pct"] < MIN_DATED_PCT:
        fails.append(f"only {out['dated_pct']}% of postings carry a date "
                     f"(need >={MIN_DATED_PCT}%) - ghosts cannot be detected")
    if out["newest_age_days"] is not None and out["newest_age_days"] > MAX_NEWEST_AGE_DAYS:
        fails.append(f"newest posting is {out['newest_age_days']} days old "
                     f"(need <={MAX_NEWEST_AGE_DAYS}) - board looks abandoned")
    if out["median_age_days"] is not None and out["median_age_days"] > MAX_MEDIAN_AGE_DAYS:
        fails.append(f"median age {out['median_age_days']} days "
                     f"(need <={MAX_MEDIAN_AGE_DAYS})")
    if out["live_pct"] < MIN_LIVE_PCT:
        fails.append(f"only {out['live_pct']}% still live after removing expired and "
                     f"stale postings (need >={MIN_LIVE_PCT}%)")
    if out["live_postings_est"] < MIN_LIVE_POSTINGS:
        fails.append(f"~{out['live_postings_est']} live postings on the whole board "
                     f"(need >={MIN_LIVE_POSTINGS}) - not enough supply to be a source")
    if out["fluff_pct"] > MAX_FLUFF_PCT:
        fails.append(f"{out['fluff_pct']}% are talent-pool/general-application fluff")

    out["failures"] = fails
    out["verdict"] = "QUALIFIED" if not fails else "REJECTED"
    return out


def render(r: Dict) -> str:
    L = [f"BOARD: {r['board']}", "-" * 62]
    if r.get("robots"):
        L.append(f"  robots.txt              {r['robots']}")
    for k, label, suf in [
        ("listings_in_sitemap", "postings in sitemap", ""),
        ("parsed", "sampled & parsed", ""),
        ("structured_data_pct", "with JobPosting data", "%"),
        ("dated_pct", "carrying a date", "%"),
        ("newest_age_days", "newest posting", " days old"),
        ("median_age_days", "median age", " days"),
        ("within_30d_pct", "posted within 30 days", "%"),
        ("expired_pct", "past own expiry date", "%  (dropped at ingest)"),
        ("fluff_pct", "talent-pool fluff", "%"),
        ("live_pct", "STILL LIVE after hygiene", "%"),
        ("live_postings_est", "live postings on board", " (est.)"),
        ("direct_ats_pct", "direct employer ATS link", "%"),
        ("gate_pass_pct", "live roles clearing gate", "%"),
    ]:
        if r.get(k) is not None:
            L.append(f"  {label:<28}{r[k]}{suf}")
    for e in r.get("errors", []):
        L.append(f"  ! {e}")
    for f in r.get("failures", []):
        L.append(f"  FAIL: {f}")
    L.append("")
    L.append(f"  VERDICT: {r.get('verdict', 'COULD NOT EVALUATE')}")
    return "\n".join(L)


async def _alert(text: str) -> None:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("[alert] TELEGRAM_BOT_TOKEN/CHAT_ID not set - not sending")
        return
    async with aiohttp.ClientSession() as s:
        await s.post(f"https://api.telegram.org/bot{token}/sendMessage",
                     json={"chat_id": chat, "text": text})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", help="board URL to qualify")
    ap.add_argument("--watch", action="store_true",
                    help="re-check the boards already wired into VJH")
    ap.add_argument("--alert", action="store_true",
                    help="send a Telegram alert if a wired board fails")
    a = ap.parse_args()

    targets = WIRED_BOARDS if a.watch else ([a.url] if a.url else [])
    if not targets:
        ap.print_help()
        return 2

    results = [asyncio.run(evaluate(t)) for t in targets]
    for r in results:
        print(render(r))
        print()

    failed = [r for r in results if r.get("verdict") != "QUALIFIED"]
    if a.watch and a.alert and failed:
        body = "\n\n".join(render(r) for r in failed)
        asyncio.run(_alert("A job board VJH depends on has degraded:\n\n" + body))

    if any("verdict" not in r for r in results):
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
