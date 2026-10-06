"""
🛡️ JOB MONITOR — CAREER-GATED EDITION

Purpose:
- Discover jobs from ATS APIs (PRIMARY SOURCE)
- Enforce career gate filtering
- Feed high-signal roles into the scoring system

This is a PRECISION CAREER WEAPON, not a volume play.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Set, Any, Optional

import aiohttp

from src.core.models import JobPosting, JobSource
from src.core.fit_gate import SOURCE_DEFAULT_MARK
from src.utils.logger import setup_logger
from src.utils.cache import ResponseCache
from src.autonomous.job_gate import JobGate

logger = setup_logger(__name__)

# ─────────────────────────────────────────────────────────
# SEEN JOBS TTL (added 2026-02-08)
# Jobs re-enter the pipeline after this many days so reposted
# or refreshed listings get re-evaluated. Jobs that were
# already APPLIED to are never re-applied.
# ─────────────────────────────────────────────────────────
SEEN_TTL_DAYS = int(__import__('os').getenv("SEEN_TTL_DAYS", "21"))


# ─────────────────────────────────────────────────────────
# HONEST SOURCE RESULT LINE (added 2026-10-06)
# From 2 Oct 02:56 UTC Torre answered every search with HTTP 400 and the log
# printed "✅ Torre.ai: 0 jobs found" every hour for four days: `if status != 200:
# continue` and `except Exception: continue` swallowed the refusals, and the last
# line could not tell "nothing matched" from "every call failed". Those two must
# never print the same line. Sources that make several requests count their
# failures and report through this one function.
# ─────────────────────────────────────────────────────────
def _source_result_line(label: str, jobs: int, failed: int, attempted: int,
                        first_error: str = "", unit: str = "requests") -> tuple:
    """Return (logging level, message) for a source's final line.

    0 jobs with failures → ❌ at WARNING; some jobs but some failures → ⚠️ at
    WARNING; no failures → ✅ at INFO (a genuine empty result stays ✅)."""
    import logging as _logging
    why = f" ({first_error})" if first_error else ""
    if failed and jobs == 0:
        return (_logging.WARNING,
                f"❌ {label}: 0 jobs — {failed}/{attempted} {unit} failed{why}")
    if failed:
        return (_logging.WARNING,
                f"⚠️ {label}: {jobs} jobs found — {failed}/{attempted} {unit} failed{why}")
    return (_logging.INFO, f"✅ {label}: {jobs} jobs found")


def _http_error(status: int, body: str) -> str:
    """'HTTP 400 {"meta":...}' — status plus the first 120 chars of the body, one line."""
    snippet = " ".join((body or "").split())[:120]
    return f"HTTP {status} {snippet}".strip()


class JobMonitor:
    """
    High-signal job discovery with career gating
    """

    def __init__(self):
        self.cache = ResponseCache(cache_dir=Path("autonomous_data/cache"))
        # New: rich seen_jobs dict  {job_id: {first_seen, last_seen, status, ...}}
        self.seen_jobs_db: Dict[str, Dict] = {}
        # Legacy compat: also keep fast lookup set for current cycle
        self.seen_jobs: Set[str] = set()
        self._load_seen_jobs()
        logger.info("🛡️ JobMonitor initialized (career gate ACTIVE)")

    # ------------------------------------------------------------------
    # Seen jobs persistence  (v2: TTL-aware, seen vs applied)
    # ------------------------------------------------------------------

    def _load_seen_jobs(self):
        """Load seen jobs. Handles both legacy (list) and new (dict) formats."""
        path = Path("autonomous_data/seen_jobs.json")
        if not path.exists():
            return

        try:
            raw = json.loads(path.read_text())
        except Exception as e:
            logger.warning(f"Failed loading seen jobs: {e}")
            return

        # ── Legacy format: {"seen_jobs": ["id1", "id2", ...]} ──
        if isinstance(raw.get("seen_jobs"), list):
            now = datetime.now(timezone.utc).isoformat()
            for job_id in raw["seen_jobs"]:
                self.seen_jobs_db[job_id] = {
                    "first_seen": now,
                    "last_seen": now,
                    "status": "seen",  # unknown if we applied — legacy data
                }
            logger.info(f"📂 Migrated {len(self.seen_jobs_db)} legacy seen jobs to TTL format")
            # Save in new format immediately
            self._save_seen_jobs()
        # ── New format: {"seen_jobs_v2": {id: {...}, ...}} ──
        elif isinstance(raw.get("seen_jobs_v2"), dict):
            self.seen_jobs_db = raw["seen_jobs_v2"]
            logger.info(f"📂 Loaded {len(self.seen_jobs_db)} seen jobs (TTL-aware)")
        else:
            logger.warning("Unknown seen_jobs format — starting fresh")

        # Build fast lookup set (only IDs that should be skipped right now)
        self._rebuild_skip_set()

    def _rebuild_skip_set(self):
        """Rebuild the fast-lookup set from the rich DB, applying TTL logic."""
        now = datetime.now(timezone.utc)
        self.seen_jobs = set()
        expired = 0

        for job_id, rec in self.seen_jobs_db.items():
            status = rec.get("status", "seen")

            # Jobs we already APPLIED to → never retry
            if status == "applied":
                self.seen_jobs.add(job_id)
                continue

            # For merely "seen" (or "skipped") jobs → apply TTL
            last_seen_str = rec.get("last_seen") or rec.get("first_seen", "")
            try:
                last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
            except Exception:
                last_seen = now  # safety fallback — treat as fresh

            age = now - last_seen
            if age < timedelta(days=SEEN_TTL_DAYS):
                self.seen_jobs.add(job_id)  # still fresh → skip
            else:
                expired += 1  # TTL expired → treat as new again

        if expired:
            logger.info(f"♻️  {expired} seen jobs expired (>{SEEN_TTL_DAYS}d) — eligible for re-evaluation")

    def _save_seen_jobs(self):
        """Persist seen jobs in v2 format (TTL-aware)."""
        path = Path("autonomous_data/seen_jobs.json")
        path.parent.mkdir(exist_ok=True)

        # Prune: keep max 3000 entries, drop oldest by last_seen
        db = self.seen_jobs_db
        if len(db) > 3000:
            sorted_ids = sorted(db, key=lambda k: db[k].get("last_seen", ""), reverse=True)
            db = {k: db[k] for k in sorted_ids[:3000]}
            self.seen_jobs_db = db

        path.write_text(json.dumps({"seen_jobs_v2": db}, indent=None))

    def mark_applied(self, job_id: str, company: str = "", title: str = ""):
        """Mark a job as APPLIED so it's never retried."""
        now = datetime.now(timezone.utc).isoformat()
        rec = self.seen_jobs_db.get(job_id, {})
        rec["status"] = "applied"
        rec["applied_at"] = now
        rec["last_seen"] = now
        if company:
            rec["company"] = company
        if title:
            rec["title"] = title
        self.seen_jobs_db[job_id] = rec
        self.seen_jobs.add(job_id)  # always skip applied jobs
        self._save_seen_jobs()

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    async def find_new_jobs(
        self,
        target_roles: List[str],
        max_results: int = 50,
    ) -> List[JobPosting]:
        """
        Main discovery pipeline
        """
        logger.info("=" * 60)
        logger.info("🔍 JOB DISCOVERY CYCLE STARTED")
        logger.info("=" * 60)

        all_jobs: List[Any] = []  # Can be JobPosting objects or dicts
        
        # Track jobs per source for summary
        source_counts = {
            "ats": 0, "dice_mcp": 0, "hn": 0, "remoteok": 0, "yc": 0,
            "wellfound": 0, "wwr": 0, "aijobs": 0, "torre": 0, "himalayas": 0, "bd_linkedin": 0,
            "yc_oss": 0,   # added 2026-07-30
            "getonbrd": 0, # added 2026-08-04 — LATAM-first, Torre-shaped
            "ai_native_builder": 0,  # added 2026-08-29 — curated AI-builder board
            "puente": 0,   # added 2026-10-06 — LATAM placement network, USD monthly pay
        }
        # 2026-10-06: per-source failure counts, written by the sources below, so
        # safe_fetch and the summary can say "❌ … n/m failed" instead of "✅ 0".
        self._source_health = {}

        # ==============================================================
        # 1️⃣ ATS APIs — PRIMARY SOURCE (Greenhouse, Lever, Workable)
        # ==============================================================
        try:
            from src.autonomous.ats_integration import get_ats_jobs_safely

            ats_jobs = await get_ats_jobs_safely(
                target_roles=target_roles,
                max_companies=40,
                # 2026-07-30: was 90s. A full ATS sweep measured 77s on Oracle for
                # 1,761 jobs (Truelogic alone: 186), so it sat right on the limit and
                # tipped over under cycle load — and asyncio.wait_for DISCARDS
                # everything on timeout, so the whole sweep returned 0. The log said
                # "returning partial results"; there are no partial results.
                timeout_seconds=240
            )

            logger.info(f"✅ ATS APIs returned {len(ats_jobs)} jobs")
            all_jobs.extend(ats_jobs)
            source_counts["ats"] = len(ats_jobs)

        except Exception as e:
            logger.error(f"❌ ATS integration failed: {e}")

        # ==============================================================
        # 1.5️⃣ DICE MCP — Tech-only job database (NEW SOURCE)
        # Additive: does NOT replace anything above
        # ==============================================================
        try:
            from src.scrapers.dice_mcp_client import get_dice_jobs_safely

            dice_jobs = await get_dice_jobs_safely(timeout_seconds=120)

            logger.info(f"✅ Dice MCP returned {len(dice_jobs)} jobs")
            all_jobs.extend(dice_jobs)
            source_counts["dice_mcp"] = len(dice_jobs)

        except Exception as e:
            logger.warning(f"⚠️ Dice MCP integration failed: {e}")

        # ==============================================================
        # 1.6️⃣ YC OSS → REAL OPENINGS (NEW SOURCE, added 2026-07-30)
        # Additive: does NOT replace anything above. Turns the free yc-oss
        # company API into actual applyable postings by fetching each hiring
        # company's public ATS board. This is what openclaw-vibejob-shortlist
        # never did — it exported companies, which cannot be applied to.
        # No auth, no cookies; workatastartup (login-gated) is NOT touched.
        # ==============================================================
        try:
            from src.scrapers.yc_oss_jobs import fetch_yc_oss_jobs

            yc_oss_jobs = await fetch_yc_oss_jobs(timeout_seconds=120)

            logger.info(f"✅ YC OSS returned {len(yc_oss_jobs)} jobs")
            all_jobs.extend(yc_oss_jobs)
            source_counts["yc_oss"] = len(yc_oss_jobs)

        except Exception as e:
            logger.warning(f"⚠️ YC OSS source failed: {e}")

        # ==============================================================
        # GET ON BOARD — LATAM-first board (added 2026-08-04)
        # A source-conversion audit over 7,087 processed jobs showed Torre alone
        # producing 88% of everything ever surfaced (36% conversion) while
        # LinkedIn managed 0 from 3,565. Torre converts because it is LATAM-first.
        # This is the same shape — and its API carries monthly USD salary plus a
        # ~2,500-char description, so pay is knowable and the thin-data guard
        # never fires on it. Verified live: 111 remote LATAM-eligible jobs,
        # 56 through iron_clad_fit, incl. an Applied AI Developer at $5,600/mo.
        # Additive: fails to [] and the cycle proceeds unchanged.
        # ==============================================================
        try:
            from src.scrapers.getonbrd_jobs import fetch_getonbrd_jobs

            gob_jobs = await fetch_getonbrd_jobs(timeout_seconds=90)

            logger.info(f"✅ Get on Board returned {len(gob_jobs)} jobs")
            all_jobs.extend(gob_jobs)
            source_counts["getonbrd"] = len(gob_jobs)

        except Exception as e:
            logger.warning(f"⚠️ Get on Board source failed: {e}")

        # ==============================================================
        # 2️⃣-7️⃣ SECONDARY SOURCES (run in parallel with timeout)
        # ==============================================================
        logger.info("🔍 Fetching from secondary sources...")
        
        # Run secondary sources in parallel with individual timeouts
        async def safe_fetch(name: str, coro, timeout: int = 15, key: str = ""):
            """Wrapper to safely fetch with timeout and error handling"""
            try:
                result = await asyncio.wait_for(coro, timeout=timeout)
                # 2026-10-06: this line printed "✅ Torre.ai (LATAM): 0 jobs" for four
                # days while every Torre call was HTTP 400. A source that reports
                # failures (key → self._source_health) gets the honest line instead.
                health = self._source_health.get(key) if key else None
                if health and health.get("failed"):
                    lvl, msg = _source_result_line(
                        name, len(result), health["failed"], health["attempted"],
                        health.get("first_error", ""), health.get("unit", "requests"))
                    logger.log(lvl, f"   {msg}")
                else:
                    logger.info(f"   ✅ {name}: {len(result)} jobs")
                return result
            except asyncio.TimeoutError:
                logger.warning(f"   ⚠️ {name}: timeout after {timeout}s")
                return []
            except Exception as e:
                logger.warning(f"   ⚠️ {name}: {str(e)[:50]}")
                return []
        
        # Run all secondary sources in parallel
        secondary_results = await asyncio.gather(
            safe_fetch("Hacker News", self._search_hackernews(), 15),
            safe_fetch("RemoteOK", self._search_remoteok(), 15),
            safe_fetch("YC WAAS", self._search_yc_workatastartup(), 20),
            safe_fetch("Wellfound", self._search_wellfound(), 20),
            safe_fetch("WeWorkRemotely", self._search_weworkremotely(), 15),
            safe_fetch("AI-Jobs.net", self._search_aijobs(), 15),
            # 2026-09-29: was 20s. Same failure as the ATS sweep above (30 Jul): asyncio.wait_for
            # DISCARDS everything on timeout. Measured on Oracle: _search_torre returns 610 jobs in
            # 24-27s (its keyword list grew 16 + 28 Sep), so from 17 Sep Torre — her LATAM-first
            # source — delivered ~0 per cycle. 90s ≈ 3x the measured run; the gather already waits
            # up to 150s (AI-Native-Builder), so the cycle is not lengthened.
            # 2026-10-06: Torre refuses VJH's request (HTTP 400 since 2 Oct, see
            # _search_torre) and now stops after 3 identical refusals, so it ends in
            # ~1 s. When it answers, 59 sequential searches ≈ 30 s (24-27 s measured
            # for ~50 on 29 Sep) — a third of this budget, so 90 s stays.
            safe_fetch("Torre.ai (LATAM)", self._search_torre(), 90, key="torre"),
            # 2026-10-06: 24 searches, 4 at a time, 8 s cap each — measured 2.1 s live
            # (all HTTP 200), ~5% of 40 s, so neither the budget nor concurrency moves.
            safe_fetch("Himalayas (global)", self._search_himalayas(), 40, key="himalayas"),
            safe_fetch("BrightData LinkedIn", self._search_brightdata_linkedin(), 60),
            # 2026-10-06: ONE feed request per 6 h now (was ~30 per cycle), see _search_remotive.
            safe_fetch("Remotive", self._search_remotive(), 20, key="remotive"),
            # 2026-08-29: ai-native-builder.com — a CURATED board, not a volume source.
            # Measured on its full 345-posting sitemap: 72.4% of it clears JobGate,
            # against ~5.6% fleet-wide, and it carries ZERO ML-researcher titles.
            # Generous timeout because the FIRST run warms a per-slug disk cache
            # (~150 detail fetches); every later run is served from cache in seconds.
            safe_fetch("AI-Native-Builder", self._search_ai_native_builder(), 150),
            # 2026-10-06: Puente Talent Partners — LATAM-only placement network, role pay
            # stated in USD per month on 49 of 53 roles (6 Oct; Elena approved the source
            # 6 Oct). First run
            # fetches ~55 role pages 4 at a time; later runs serve them from the
            # in-process cache, so only the listing page is fetched.
            safe_fetch("Puente (LATAM placement)", self._search_puente(), 45, key="puente"),
            return_exceptions=True
        )

        # Unpack results
        hn_jobs, remoteok_jobs, yc_jobs, wellfound_jobs, wwr_jobs, ai_jobs, torre_jobs, himalayas_jobs, bd_linkedin_jobs, remotive_jobs, anb_jobs, puente_jobs = secondary_results

        # Handle any exceptions that slipped through
        for name, jobs in [("hn", hn_jobs), ("remoteok", remoteok_jobs),
                           ("yc", yc_jobs), ("wellfound", wellfound_jobs),
                           ("wwr", wwr_jobs), ("aijobs", ai_jobs),
                           ("torre", torre_jobs), ("himalayas", himalayas_jobs),
                           ("bd_linkedin", bd_linkedin_jobs), ("remotive", remotive_jobs),
                           ("ai_native_builder", anb_jobs), ("puente", puente_jobs)]:
            if isinstance(jobs, Exception):
                logger.warning(f"   ⚠️ {name} exception: {jobs}")
                jobs = []
            if isinstance(jobs, list):
                all_jobs.extend(jobs)
                source_counts[name] = len(jobs)

        # ==============================================================
        # 📊 SOURCE SUMMARY (visibility into what's working)
        # ==============================================================
        logger.info("=" * 60)
        logger.info("📊 SOURCE SUMMARY:")
        logger.info(f"   ATS APIs:        {source_counts['ats']} jobs")
        logger.info(f"   Dice MCP:        {source_counts['dice_mcp']} jobs")
        logger.info(f"   YC OSS (openings):{source_counts['yc_oss']} jobs")
        logger.info(f"   Get on Board:    {source_counts['getonbrd']} jobs")
        logger.info(f"   Hacker News:     {source_counts['hn']} jobs")
        logger.info(f"   RemoteOK:        {source_counts['remoteok']} jobs")
        logger.info(f"   YC WAAS:         {source_counts['yc']} jobs")
        logger.info(f"   Wellfound:       {source_counts['wellfound']} jobs")
        logger.info(f"   WeWorkRemotely:  {source_counts['wwr']} jobs")
        logger.info(f"   AI-Jobs.net:     {source_counts['aijobs']} jobs")
        # 2026-10-06: a source whose calls failed says so here too — "0 jobs" alone
        # read as "nothing matched" for the four days Torre was refusing every call.
        def _fail_tag(key: str) -> str:
            h = self._source_health.get(key) or {}
            if not h.get("failed"):
                return ""
            return f"  ❌ {h['failed']}/{h['attempted']} {h.get('unit', 'requests')} failed"
        logger.info(f"   Torre.ai (LATAM):{source_counts['torre']} jobs{_fail_tag('torre')}")
        logger.info(f"   Puente (LATAM):  {source_counts.get('puente', 0)} jobs{_fail_tag('puente')}")
        logger.info(f"   Himalayas (glbl):{source_counts['himalayas']} jobs{_fail_tag('himalayas')}")
        logger.info(f"   BrightData LI:   {source_counts['bd_linkedin']} jobs")
        logger.info(f"   Remotive:        {source_counts.get('remotive', 0)} jobs{_fail_tag('remotive')}")
        logger.info(f"   AI-Native-Bldr:  {source_counts.get('ai_native_builder', 0)} jobs")
        logger.info(f"   TOTAL:           {len(all_jobs)} jobs")
        logger.info("=" * 60)

        # Prioritize region-tagged remote-first sources (Torre/Remotive/RemoteOK/WWR/Himalayas)
        # BEFORE the gate + max_results cap, so Elena's LATAM/remote AI jobs are not crowded out
        # by the ~1700 generic ATS jobs. (JobPosting.source is lost to OTHER on conversion, so we
        # read the raw dict's "source" here while it still exists.)
        # 2026-07-30: added "yc_oss" — the new YC-companies→real-openings source. Without it
        # here, its ~130 postings sit behind ~1700 generic ATS jobs and get cut by max_results,
        # which is exactly how the region-tagged sources were starved in June.
        # 2026-08-29: added "ai_native_builder" for the SAME reason yc_oss was added on
        # 07-30. It is the highest-converting source in the fleet by measured gate rate
        # (72.4% vs ~5.6%), so leaving it out of this list would bury its ~345 postings
        # behind ~1700 generic ATS jobs and let max_results cut the best supply we have.
        # Round-robin order: richest source first WITHIN each round. This is a
        # tie-break, not a quota — every source still gets one slot per round, so
        # nothing here can starve anything below it. Percentages are measured gate
        # pass rates, not guesses; re-measure before reordering.
        _SRC_YIELD_ORDER = (
            "ai_native_builder",   # 72% gate pass, measured 2026-08-30
            "torre",               # the long-standing best converter (LATAM-first)
            "puente",              # 2026-10-06: LATAM-only placement; measured live 6 Oct: JobGate 23/53 (43%)
            "getonbrd",            # LATAM, carries real salary data
            "remotive",
            "yc_oss",
            "remoteok",
            "weworkremotely",
            "himalayas",
            "wellfound",
            "aijobs",
        )
        _PRIO_SRC = _SRC_YIELD_ORDER  # kept: other call sites read this name
        def _job_src(j):
            if isinstance(j, dict):
                return (j.get("source") or "").lower()
            try:
                return (j.model_dump().get("source") or "").lower()
            except Exception:
                return str(getattr(j, "source", "")).lower()
        # 2026-08-30 — REPLACED a binary sort with round-robin interleaving.
        #
        # The old line was `sort(key=0 if source in _PRIO_SRC else 1)`. That is a
        # GROUP, not a RANKING, and a stable sort preserves append order inside the
        # group. ai_native_builder is appended last among the priority sources, so
        # ~888 jobs from Torre/getonbrd/yc_oss queued ahead of it and the
        # max_results cap (120) was exhausted long before the board was reached.
        # Measured 2026-08-30: 279 of its postings sat in seen_jobs and EVERY ONE
        # had status='seen' — not one had ever reached LangGraph. The densest source
        # in the fleet (72% gate pass vs ~21%) was contributing exactly nothing.
        #
        # Round-robin fixes the class of bug rather than this instance: one job per
        # source per round, richest source first within the round. No source can
        # crowd out another no matter how much volume it brings, so adding a big new
        # source can never again silently starve an existing one.
        def _interleave_by_source(jobs: List) -> List:
            buckets: Dict[str, List] = {}
            for j in jobs:
                s = _job_src(j)
                key = next((p for p in _SRC_YIELD_ORDER if p in s), "_other")
                buckets.setdefault(key, []).append(j)
            order = [k for k in _SRC_YIELD_ORDER if k in buckets]
            if "_other" in buckets:
                order.append("_other")
            out: List = []
            cursor = {k: 0 for k in order}
            while len(out) < len(jobs):
                moved = False
                for k in order:
                    i = cursor[k]
                    if i < len(buckets[k]):
                        out.append(buckets[k][i])
                        cursor[k] = i + 1
                        moved = True
                if not moved:
                    break
            return out

        all_jobs = _interleave_by_source(all_jobs)

        # ==============================================================
        # 4️⃣ CAREER GATE FILTERING
        # ==============================================================
        before_gate = len(all_jobs)
        gated_jobs = []
        
        for job in all_jobs:
            # Convert JobPosting objects to dict for gate
            if hasattr(job, 'to_dict'):
                job_dict = job.to_dict()
            elif hasattr(job, 'model_dump'):
                job_dict = job.model_dump()
            elif isinstance(job, dict):
                job_dict = job
            else:
                job_dict = {"title": str(job), "description": "", "location": ""}
            
            if JobGate.passes(job_dict):
                gated_jobs.append(job)

        pass_rate = (len(gated_jobs)/before_gate*100) if before_gate > 0 else 0
        logger.info(f"🛡️ Career gate: {len(gated_jobs)}/{before_gate} jobs passed ({pass_rate:.1f}%)")

        # ==============================================================
        # 5️⃣ Deduplicate + Convert to JobPosting  (v2: TTL-aware)
        # ==============================================================
        new_jobs: List[JobPosting] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 2026-08-30 — MARK-SEEN NOW HAPPENS AFTER THE CAP, NOT BEFORE IT.
        #
        # The previous version marked every gate-passing job as seen, persisted that,
        # logged "N NEW jobs accepted", and THEN did `return new_jobs[:max_results]`.
        # Everything past the cap was recorded as "we have looked at this" without
        # anyone ever looking at it, and SEEN_TTL_DAYS=21 kept it buried for three
        # weeks — long enough for a posting to expire. On 2026-08-29 that read:
        #
        #     🎯 295 NEW jobs accepted (not seen before)
        #     ✅ Found 120 new jobs
        #
        # 175 jobs burned in one cycle, under a log line announcing success. This is
        # the house failure mode — silence shaped like success — so the fix is
        # structural: a job is marked seen if and only if it is being returned.
        accepted: List = []          # (job_id, raw job) actually being returned
        in_cycle: Set[str] = set()   # in-cycle dedupe, NOT persisted

        for job in gated_jobs:
            if len(new_jobs) >= max_results:
                break                # stop before touching anything we cannot process

            job_id = self._job_id(job)
            if job_id in self.seen_jobs or job_id in in_cycle:
                continue
            in_cycle.add(job_id)

            # Convert to JobPosting if needed.
            # 2026-09-01: one malformed record must never kill the cycle. A source
            # emitting a null company took down every run until this was wrapped —
            # 2,000+ good jobs discarded because one was bad. Skip the record, log
            # which source produced it, and keep going.
            try:
                if isinstance(job, JobPosting):
                    posting = job
                elif hasattr(job, 'to_dict') or hasattr(job, 'model_dump'):
                    posting = self._ats_job_to_posting(job)
                else:
                    posting = self._dict_to_job_posting(job)
            except Exception as e:
                src = job.get("source", "?") if isinstance(job, dict) else "?"
                ttl = job.get("title", "?") if isinstance(job, dict) else "?"
                logger.warning(
                    "   ⚠️ skipping malformed job from '%s' (%s): %s",
                    src, str(ttl)[:48], str(e).splitlines()[0][:110])
                in_cycle.discard(job_id)   # not seen, so a fixed version can return
                continue

            # A posting with no company cannot be applied to and reads as a blank
            # card in the CRM. Drop it here rather than downstream.
            if not (posting.company or "").strip():
                logger.warning("   ⚠️ skipping job with no company: %s",
                               (posting.title or "?")[:60])
                in_cycle.discard(job_id)
                continue

            new_jobs.append(posting)
            accepted.append((job_id, job))

        # Persist 'seen' ONLY for what is being handed to the pipeline.
        for job_id, job in accepted:
            job_dict = job if isinstance(job, dict) else (job.to_dict() if hasattr(job, 'to_dict') else {})
            self.seen_jobs_db[job_id] = {
                "first_seen": self.seen_jobs_db.get(job_id, {}).get("first_seen", now_iso),
                "last_seen": now_iso,
                "status": "seen",
                "company": job_dict.get("company", "") if isinstance(job_dict, dict) else getattr(job, 'company', ''),
                "title": job_dict.get("title", "") if isinstance(job_dict, dict) else getattr(job, 'title', ''),
            }
            self.seen_jobs.add(job_id)

        self._save_seen_jobs()

        deferred = len(gated_jobs) - len(new_jobs)
        logger.info(f"🎯 {len(new_jobs)} NEW jobs accepted and marked seen (cap {max_results})")
        if deferred > 0:
            # Deferred, NOT dropped: these were never marked seen, so the next cycle
            # reconsiders them immediately instead of in 21 days.
            logger.info(f"   ↩️  {deferred} gate-passing jobs left UNSEEN for the next cycle")
        logger.info("=" * 60)

        return new_jobs

    # ------------------------------------------------------------------
    # Additional Sources
    # ------------------------------------------------------------------

    async def _search_hackernews(self) -> List[Dict]:
        """Hacker News Who's Hiring via Algolia API"""
        logger.info("🔍 Checking Hacker News Who's Hiring...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                # Find latest "Who is Hiring" thread
                url = "https://hn.algolia.com/api/v1/search"
                params = {"query": "who is hiring", "tags": "ask_hn", "hitsPerPage": 1}

                async with session.get(url, params=params, timeout=10) as resp:
                    data = await resp.json()
                    if not data.get("hits"):
                        return jobs
                    thread_id = data["hits"][0]["objectID"]

                # Get thread comments
                async with session.get(
                    f"https://hn.algolia.com/api/v1/items/{thread_id}",
                    timeout=15,
                ) as resp:
                    thread = await resp.json()

                    for comment in thread.get("children", [])[:100]:  # First 100 comments
                        text = comment.get("text", "") or ""
                        text_lower = text.lower()

                        # Filter for relevant keywords
                        if any(k in text_lower for k in ["ai", "ml", "founding", "engineer", "startup"]):
                            jobs.append({
                                "title": "AI/ML Engineer",
                                "company": "HN Startup",
                                "location": "Remote",
                                "description": text[:2000],
                                "source": "hackernews",
                                "url": f"https://news.ycombinator.com/item?id={comment.get('id')}",
                            })

            logger.info(f"✅ HN: {len(jobs)} relevant jobs found")

        except Exception as e:
            logger.warning(f"⚠️ HN fetch failed: {e}")

        return jobs

    async def _search_remoteok(self) -> List[Dict]:
        """RemoteOK JSON API"""
        logger.info("🔍 Checking RemoteOK...")
        jobs = []
        seen = set()
        # The generic /api feed is mostly VA/admin/marketing; pull the DEV + AI tag feeds.
        feeds = [
            "https://remoteok.com/remote-dev-jobs.json",
            "https://remoteok.com/api?tags=ai",
            "https://remoteok.com/api?tags=machine-learning",
            # 2026-07-30: AI-automation category tags (additive).
            "https://remoteok.com/api?tags=automation",
            "https://remoteok.com/api?tags=no-code",
        ]
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "Mozilla/5.0 (VibeJobHunter)"}
                for url in feeds:
                    try:
                        async with session.get(url, headers=headers, timeout=15) as resp:
                            if resp.status != 200:
                                continue
                            data = await resp.json()
                    except Exception:
                        continue
                    for item in (data or []):
                        if not isinstance(item, dict):
                            continue
                        title = item.get("position") or ""
                        tl = title.lower()
                        if not any(k in tl for k in ["ai", "ml", "engineer", "developer", "data",
                                                     "founding", "software", "machine learning", "automation"]):
                            continue
                        jid = item.get("id") or item.get("slug") or title
                        if jid in seen:
                            continue
                        seen.add(jid)
                        loc = (item.get("location") or "").strip()
                        jobs.append({
                            "title":       title,
                            "company":     item.get("company", ""),
                            "location":    "Remote — " + (loc if loc else "Worldwide"),  # no loc = worldwide (LATAM-ok)
                            "description": (item.get("description") or "")[:2000],
                            "source":      "remoteok",
                            "url":         item.get("url", "") or ("https://remoteok.com" + (item.get("slug", "") or "")),
                        })
            logger.info(f"✅ RemoteOK: {len(jobs)} relevant jobs found")
        except Exception as e:
            logger.warning(f"⚠️ RemoteOK failed: {e}")
        return jobs

    def _record_health(self, key: str, failed: int, attempted: int,
                       first_error: str = "", unit: str = "requests") -> None:
        """2026-10-06: let safe_fetch and the SOURCE SUMMARY see that a source's
        calls failed, so an empty result is never reported as a clean ✅."""
        self.__dict__.setdefault("_source_health", {})[key] = {
            "failed": failed, "attempted": attempted,
            "first_error": first_error, "unit": unit,
        }

    # 2026-10-06 — Remotive feed cache. Measured today: the free API IGNORES
    # `search` — the unfiltered feed and ?search=AI%20automation return the same 18
    # job ids — and its own notice says "excessive requests (more than 2x per
    # minute) will be blocked … we advise max. 4 times a day". The old loop sent ~30
    # identical requests every hourly cycle. One fetch per 6 h, held in-process.
    _REMOTIVE_TTL_S = 6 * 3600
    _REMOTIVE_CACHE: Dict[str, Any] = {}

    @staticmethod
    def _remotive_matches(item: Dict, terms) -> bool:
        """Case-insensitive partial match over title + description — what Remotive
        documents its `search` parameter as doing, applied locally (2026-10-06)."""
        import re as _re
        blob = f"{item.get('title', '')} {_re.sub(r'<[^>]+>', ' ', item.get('description', '') or '')}".lower()
        return any(t.lower() in blob for t in terms)

    async def _search_remotive(self) -> List[Dict]:
        """Remotive — remote-first, REGION-TAGGED board (free, no key). Its
        candidate_required_location field ('Worldwide' / 'Americas' / 'LATAM' /
        'USA' / 'Brazil') feeds the iron-clad gate a REAL region instead of a guess,
        so remote + LATAM-friendly + AI-augmented roles surface reliably. This is the
        source that found Elena's first real targets (A.Team / EverAI / Miris)."""
        import re as _re
        import time as _time
        logger.info("🔍 Checking Remotive...")
        jobs: List[Dict] = []
        seen_ids = set()
        # 2026-07-30: APPENDED the AI-automation category (agent builders, n8n/Make/Zapier
        # shops, AI integration). This is Elena's demonstrated, shipped skill set — 10 live
        # agents, the Make+Fable 5 concierge, WHITESPACE — and it pays $3-6K/mo remote, yet
        # it was almost absent from what VJH searched. Original 5 terms kept untouched.
        queries = ["AI automation", "no-code", "AI agent", "AI solutions", "prompt",
                   "AI automation engineer", "AI agent developer", "automation engineer",
                   "n8n", "make.com", "Zapier", "workflow automation",
                   "AI integration engineer", "AI implementation", "forward deployed engineer",
                   # 2026-08-18: AI chief-of-staff / AI-proficient EA-PA lane — same
                   # supply-gap fix as Torre (job_gate.py / fit_gate.py already carve
                   # these titles through; they were never being SEARCHED for here).
                   "AI chief of staff", "AI operations lead", "AI executive assistant",
                   "AI personal assistant",
                   # 2026-09-16: AI product / consulting / leadership lanes — the judge and
                   # the scoring prompt now approve these (src/core/target_lanes.py), so
                   # supply has to ask for them too.
                   "AI product manager", "chief AI officer", "head of AI", "AI consultant",
                   "AI program manager", "AI transformation", "solutions consultant",
                   # 2026-09-28: creative AI lane (src/core/target_lanes.py) — never searched before.
                   "creative technologist", "generative AI producer", "AI video producer",
                   "AI filmmaker",
                   # 2026-10-06: Professional Outlook (Oct 2026, p.7 "Where I fit") titles
                   # not already covered above, across her three lanes.
                   "AI implementation lead", "AI workflow architect", "agentic workflow",
                   "AI systems operator", "AI innovation lead", "generative AI product lead",
                   "AI prototyping", "creative AI pipeline", "AI product automation",
                   "AI adoption", "GenAI production"]
        # 2026-10-06: the terms above are matched LOCALLY against one cached feed
        # (see _REMOTIVE_CACHE) — the API ignores `search`, and ~30 requests an hour
        # broke Remotive's published limit of 2 a minute.
        cache = self._REMOTIVE_CACHE
        items = cache.get("items")
        fetched_now = False
        if items is None or _time.time() - cache.get("at", 0) > self._REMOTIVE_TTL_S:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"User-Agent": "VibeJobHunter/1.0"}
                    async with session.get("https://remotive.com/api/remote-jobs",
                                           headers=headers, timeout=15) as resp:
                        if resp.status != 200:
                            err = _http_error(resp.status, await resp.text())
                            logger.warning(f"⚠️ Remotive feed: {err}")
                            self._record_health("remotive", 1, 1, err)
                            lvl, msg = _source_result_line("Remotive", 0, 1, 1, err)
                            logger.log(lvl, msg)
                            return jobs
                        data = await resp.json(content_type=None)
                items = (data or {}).get("jobs", []) if isinstance(data, dict) else []
                cache.update(items=items, at=_time.time())
                fetched_now = True
            except Exception as e:
                err = f"{type(e).__name__}: {str(e)[:120]}"
                logger.warning(f"⚠️ Remotive feed failed: {err}")
                self._record_health("remotive", 1, 1, err)
                lvl, msg = _source_result_line("Remotive", 0, 1, 1, err)
                logger.log(lvl, msg)
                return jobs
        self._record_health("remotive", 0, 1)
        for item in items:
            jid = item.get("id")
            if jid in seen_ids or not self._remotive_matches(item, queries):
                continue
            seen_ids.add(jid)
            region = (item.get("candidate_required_location") or "Worldwide").strip()
            desc = _re.sub(r"<[^>]+>", " ", item.get("description", "") or "")
            jobs.append({
                "title":       item.get("title", ""),
                "company":     item.get("company_name", ""),
                "location":    "Remote — " + region,  # guarantees remote + real region tag
                "description": desc[:2000],
                "source":      "remotive",
                "url":         item.get("url", ""),
            })
        logger.info(f"✅ Remotive: {len(jobs)} jobs found ({len(jobs)}/{len(items)} feed jobs "
                    f"match the lane terms; feed {'fetched now' if fetched_now else 'from the 6 h cache'})")
        return jobs

    async def _search_ai_native_builder(self) -> List[Dict]:
        """ai-native-builder.com — a CURATED board for people who BUILD with AI tools
        rather than train models. This is a signal-density source, not a volume one:
        measured over its full 345-posting sitemap on 2026-08-29, 72.4% cleared JobGate
        (fleet-wide is ~5.6%) and ZERO postings carried an ML-researcher title, which is
        Elena's single largest discard bucket everywhere else.

        Ingest is the publisher's own machine-readable data — sitemap.xml plus a
        schema.org JobPosting JSON-LD block on every job page — under a robots.txt that
        reads 'User-Agent: * / Allow: /'. No key, no auth, no paywall. Fails soft to []."""
        try:
            from src.scrapers.ai_native_builder import fetch_ai_native_builder_jobs
            return await fetch_ai_native_builder_jobs()
        except Exception as e:
            logger.warning(f"⚠️ ai-native-builder source failed: {e}")
            return []

    async def _search_yc_workatastartup(self) -> List[Dict]:
        """
        YC Work At A Startup - FIXED API
        
        Multiple fallback methods:
        1. Direct Algolia API (public endpoint)
        2. Companies JSON endpoint
        3. Jobs listing scrape
        
        FIXED: December 2025 - More reliable API access
        """
        # DISABLED June 2026, and RE-CONFIRMED 2026-08-29 for a stronger reason.
        #
        # The original note said "login-gated, no free API". That is no longer the
        # whole truth and it invited a future session to go looking for a way in:
        # www.workatastartup.com/jobs is in fact PUBLIC again (Rails + Inertia, the
        # payload sits in the data-page attribute, ~30 jobs with title, location,
        # salary on 26/30, company, batch and applyUrl). It is easy to parse.
        #
        # We still do not touch it. Y Combinator's terms of service state:
        #     "In connection with your use of the Site you will not engage in or use
        #      any data mining, robots, scraping or similar data gathering or
        #      extraction methods."
        # That governs all YC properties including workatastartup.com. robots.txt on
        # that host says "Disallow:" (allow all), but robots.txt is a crawler hint and
        # the ToS is a deliberate statement of intent. When they disagree, the ToS wins.
        #
        # Doing it anyway would also be bad business: the public page yielded 4/30
        # through the career gate (13%, and 24 of 30 were onsite), and using Elena's
        # own WaaS session to reach the full board would put a real account she needs
        # at risk of a ban. WaaS is a DEMAND channel for her — YC founders search it
        # for candidates — so the account is worth more to her intact than scraped.
        #
        # YC coverage therefore comes from src/scrapers/yc_oss_jobs.py instead, which
        # reads the community yc-oss dataset plus each company's OWN public ATS board
        # (Greenhouse/Ashby/Lever APIs). Different systems, no YC ToS involved.
        logger.info("⏭️  YC WAAS: deliberately not scraped (YC ToS forbids automated "
                    "extraction) — YC coverage comes from yc_oss + company ATS boards")
        return []

        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                # METHOD 1: Try the public jobs listing API first (most reliable)
                jobs = await self._yc_method_jobs_api(session)
                
                if jobs:
                    logger.info(f"✅ YC WAAS (jobs API): {len(jobs)} jobs found")
                    return jobs
                
                # METHOD 2: Try Algolia search
                jobs = await self._yc_method_algolia(session)
                
                if jobs:
                    logger.info(f"✅ YC WAAS (algolia): {len(jobs)} jobs found")
                    return jobs
                
                # METHOD 3: Scrape companies page
                jobs = await self._yc_method_companies_scrape(session)
                
                if jobs:
                    logger.info(f"✅ YC WAAS (scrape): {len(jobs)} jobs found")
                    return jobs
                
                logger.warning("⚠️ All YC WAAS methods failed - 0 jobs")
                return []

        except Exception as e:
            logger.warning(f"⚠️ YC WAAS failed: {e}")
            return []
    
    async def _yc_method_jobs_api(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Method 1: Direct jobs API endpoint"""
        jobs = []
        
        try:
            # YC has a public jobs API endpoint
            url = "https://www.workatastartup.com/jobs"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/html",
            }
            
            # Try JSON endpoint first
            json_url = "https://www.workatastartup.com/jobs.json"
            
            async with session.get(json_url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('content-type', '')
                    if 'json' in content_type:
                        data = await resp.json()
                        
                        for job_data in data.get('jobs', data) if isinstance(data, dict) else data[:100]:
                            if isinstance(job_data, dict):
                                jobs.append(self._parse_yc_job(job_data))
                        
                        return jobs
            
        except Exception as e:
            logger.debug(f"YC jobs API failed: {e}")
        
        return jobs
    
    async def _yc_method_algolia(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Method 2: Algolia search API"""
        jobs = []
        
        try:
            # YC uses Algolia for search
            # Public API key from their website
            algolia_url = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"
            
            # This is the PUBLIC search-only API key embedded in their website
            headers = {
                "x-algolia-api-key": "OWI5MWY3MzYyYTliZDNmMWZkYmY2Zjk0MjdlYmVkNDc3ZDZmNGE3ZjNmMGQxMTc4ZGU4MTU4NTdlNmUxOTE0YXJlc3RyaWN0SW5kaWNlcz1XYWFTX3Byb2R1Y3Rpb25fam9iX3Bvc3RpbmdzJTJDV2FhU19wcm9kdWN0aW9uX2NvbXBhbmllcw==",
                "x-algolia-application-id": "45BWZJ1SGC",
                "Content-Type": "application/json",
            }
            
            # Search queries
            search_queries = [
                "AI engineer",
                "founding engineer",
                "machine learning",
                "full stack engineer",
                "software engineer",
            ]
            
            requests = []
            for query in search_queries:
                requests.append({
                    "indexName": "WaaS_production_job_postings",
                    "params": f"query={query}&hitsPerPage=30"
                })
            
            payload = {"requests": requests}
            
            async with session.post(algolia_url, json=payload, headers=headers, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    seen_ids = set()
                    for result in data.get("results", []):
                        for hit in result.get("hits", []):
                            job_id = hit.get("id") or hit.get("objectID")
                            if job_id in seen_ids:
                                continue
                            seen_ids.add(job_id)
                            
                            jobs.append(self._parse_yc_algolia_hit(hit, job_id))
                else:
                    logger.debug(f"Algolia returned {resp.status}")
                    
        except Exception as e:
            logger.debug(f"YC Algolia failed: {e}")
        
        return jobs
    
    async def _yc_method_companies_scrape(self, session: aiohttp.ClientSession) -> List[Dict]:
        """Method 3: Scrape companies page for embedded JSON"""
        jobs = []
        
        try:
            url = "https://www.workatastartup.com/companies"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            
            # Try with query params
            params = {
                "industry": "B2B",
                "hasJobs": "true",
            }
            
            async with session.get(url, headers=headers, params=params, timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    
                    # Look for __NEXT_DATA__ or embedded JSON
                    import re
                    
                    # Pattern 1: Next.js data
                    next_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html, re.DOTALL)
                    if next_match:
                        try:
                            next_data = json.loads(next_match.group(1))
                            page_props = next_data.get("props", {}).get("pageProps", {})
                            
                            # Extract jobs from various possible locations
                            companies = page_props.get("companies", []) or page_props.get("results", [])
                            
                            for company in companies[:50]:
                                company_jobs = company.get("jobs", [])
                                for job_data in company_jobs:
                                    jobs.append({
                                        "id": f"yc_{job_data.get('id', '')}",
                                        "title": job_data.get("title", ""),
                                        "company": company.get("name", "YC Startup"),
                                        "location": job_data.get("location", "Remote"),
                                        "description": job_data.get("description", "")[:2000],
                                        "source": "yc_workatastartup",
                                        "url": job_data.get("url") or f"https://www.workatastartup.com/jobs/{job_data.get('id')}",
                                        "remote": job_data.get("remote", True),
                                    })
                        except json.JSONDecodeError:
                            pass
                    
                    # Pattern 2: Companies JSON in script
                    json_match = re.search(r'"companies":\s*(\[[^\]]+\])', html)
                    if json_match and not jobs:
                        try:
                            companies = json.loads(json_match.group(1))
                            for company in companies[:30]:
                                jobs.append({
                                    "id": f"yc_{company.get('id', '')}",
                                    "title": "Engineering Role",
                                    "company": company.get("name", "YC Startup"),
                                    "location": "Remote",
                                    "description": company.get("description", ""),
                                    "source": "yc_workatastartup",
                                    "url": f"https://www.workatastartup.com/companies/{company.get('slug', '')}",
                                })
                        except json.JSONDecodeError:
                            pass
                            
        except Exception as e:
            logger.debug(f"YC companies scrape failed: {e}")
        
        return jobs
    
    def _parse_yc_job(self, job_data: Dict) -> Dict:
        """Parse a YC job from their API - WITH PREMIUM FLAGS"""
        return {
            "id": f"yc_{job_data.get('id', '')}",
            "title": job_data.get("title", "") or job_data.get("job_title", ""),
            "company": job_data.get("company_name", "") or job_data.get("company", {}).get("name", "YC Startup"),
            "location": job_data.get("location", "Remote"),
            "description": (job_data.get("description", "") or job_data.get("job_description", ""))[:2000],
            "source": "yc_workatastartup",
            "url": job_data.get("url") or f"https://www.workatastartup.com/jobs/{job_data.get('id')}",
            "salary_min": job_data.get("salary_min"),
            "salary_max": job_data.get("salary_max"),
            "remote": job_data.get("remote", True),
            "yc_batch": job_data.get("batch"),
            # 🏆 PREMIUM FLAGS - YC Advantage
            "is_yc_company": True,
            "is_premium_source": True,
            "score_boost": 15,  # +15 points for YC companies!
        }
    
    def _parse_yc_algolia_hit(self, hit: Dict, job_id: str) -> Dict:
        """Parse an Algolia search hit into a job dict"""
        title = hit.get("title") or hit.get("job_title") or ""
        company = hit.get("company_name") or "YC Startup"
        if isinstance(hit.get("company"), dict):
            company = hit["company"].get("name", company)
        
        location = hit.get("location") or hit.get("locations") or "Remote"
        if isinstance(location, list):
            location = ", ".join(str(l) for l in location[:3])
        
        description = hit.get("description") or hit.get("job_description") or ""
        
        return {
            "id": f"yc_{job_id}",
            "title": title,
            "company": company,
            "location": str(location),
            "description": description[:2000],
            "source": "yc_workatastartup",
            "url": f"https://www.workatastartup.com/jobs/{job_id}",
            "salary_min": hit.get("salary_min"),
            "salary_max": hit.get("salary_max"),
            "remote": hit.get("remote", True),
            "yc_batch": hit.get("batch") or (hit.get("company", {}) if isinstance(hit.get("company"), dict) else {}).get("batch"),
            # 🏆 PREMIUM FLAGS - YC Advantage
            "is_yc_company": True,
            "is_premium_source": True,
            "score_boost": 15,  # +15 points for YC companies!
        }
    
    async def _search_wellfound(self) -> List[Dict]:
        """
        Wellfound (formerly AngelList Talent) — DORMANT since 2026-08-30.

        It was returning `✅ Wellfound: 0 jobs found` on every cycle: a green tick over
        zero output, and — unlike AI-Jobs.net and BrightData LinkedIn — it was never
        marked dormant, so nothing ever prompted anyone to look. A source that reports
        success while delivering nothing is worse than one that reports failure,
        because it consumes the attention budget that would have found the problem.

        WHY IT RETURNS ZERO: the code below POSTs to https://wellfound.com/graphql with
        a hand-guessed `operationName: "JobSearchResults"`. That is Wellfound's private
        internal API. Nobody published it, nobody promised to keep it stable, and it
        changed.

        WHY WE ARE NOT FIXING IT BY TRYING HARDER: same call as YC Work at a Startup on
        2026-08-29. Reverse-engineering a company's private GraphQL endpoint to extract
        listings is exactly the automated-extraction that these platforms' terms exist
        to forbid, and re-guessing the schema every time they ship a release is not a
        source, it is a treadmill. VJH already has fourteen sources that publish their
        data deliberately.

        Set VJH_WELLFOUND_ENABLED=true to wake the old code path (it is untouched below).
        """
        import os as _os
        if _os.getenv("VJH_WELLFOUND_ENABLED", "false").strip().lower() != "true":
            logger.info("⏭️  Wellfound: dormant (private GraphQL API changed; "
                        "0 jobs for months behind a green log line — "
                        "VJH_WELLFOUND_ENABLED=true to wake)")
            return []

        logger.info("🔍 Checking Wellfound (AngelList)...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                # Wellfound GraphQL endpoint
                graphql_url = "https://wellfound.com/graphql"
                
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Origin": "https://wellfound.com",
                    "Referer": "https://wellfound.com/jobs",
                }
                
                # GraphQL query for job listings
                queries = [
                    {"role": "AI Engineer", "remote": True},
                    {"role": "Founding Engineer", "remote": False},
                    {"role": "Machine Learning Engineer", "remote": True},
                    {"role": "Staff Engineer", "remote": True},
                    # 2026-08-18: AI chief-of-staff / AI-proficient EA-PA lane.
                    {"role": "AI Chief of Staff", "remote": True},
                    {"role": "AI Executive Assistant", "remote": True},
                ]
                
                for query_params in queries:
                    graphql_query = {
                        "operationName": "JobSearchResults",
                        "variables": {
                            "query": query_params["role"],
                            "page": 1,
                            "perPage": 30,
                            "remote": query_params["remote"],
                            "sortBy": "posted_at",
                        },
                        "query": """
                            query JobSearchResults($query: String, $page: Int, $perPage: Int, $remote: Boolean) {
                                jobListings(query: $query, page: $page, perPage: $perPage, remote: $remote) {
                                    edges {
                                        node {
                                            id
                                            title
                                            slug
                                            remote
                                            locationNames
                                            compensation
                                            description
                                            startup {
                                                name
                                                slug
                                                companySize
                                                highConcept
                                            }
                                        }
                                    }
                                }
                            }
                        """
                    }
                    
                    try:
                        async with session.post(
                            graphql_url,
                            json=graphql_query,
                            headers=headers,
                            timeout=15
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                
                                edges = data.get("data", {}).get("jobListings", {}).get("edges", [])
                                
                                for edge in edges:
                                    node = edge.get("node", {})
                                    startup = node.get("startup", {})
                                    
                                    job_id = node.get("id", "")
                                    slug = node.get("slug", "")
                                    startup_slug = startup.get("slug", "")
                                    
                                    jobs.append({
                                        "id": f"wellfound_{job_id}",
                                        "title": node.get("title", ""),
                                        "company": startup.get("name", ""),
                                        "location": ", ".join(node.get("locationNames", ["Remote"])[:3]),
                                        "description": (node.get("description") or startup.get("highConcept") or "")[:2000],
                                        "source": "wellfound",
                                        "url": f"https://wellfound.com/jobs/{slug}" if slug else "https://wellfound.com/jobs",
                                        "compensation": node.get("compensation"),
                                        "company_size": startup.get("companySize"),
                                        "remote": node.get("remote", False),
                                    })
                            else:
                                logger.debug(f"Wellfound returned {resp.status}")
                                
                    except Exception as e:
                        logger.debug(f"Wellfound query for '{query_params['role']}' failed: {e}")
                
                # Fallback: Try the public job listings page
                if len(jobs) == 0:
                    try:
                        # Simple HTML scrape fallback
                        search_url = "https://wellfound.com/role/r/ai-engineer"
                        async with session.get(search_url, headers=headers, timeout=15) as resp:
                            if resp.status == 200:
                                html = await resp.text()
                                # Basic parsing - look for job data in script tags
                                if "__NEXT_DATA__" in html:
                                    import re
                                    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html)
                                    if match:
                                        try:
                                            next_data = json.loads(match.group(1))
                                            # Extract job listings from Next.js data
                                            page_props = next_data.get("props", {}).get("pageProps", {})
                                            listings = page_props.get("jobListings", []) or page_props.get("results", [])
                                            
                                            for listing in listings[:20]:
                                                jobs.append({
                                                    "id": f"wellfound_{listing.get('id', '')}",
                                                    "title": listing.get("title", "AI Engineer"),
                                                    "company": listing.get("company", {}).get("name", "Startup"),
                                                    "location": listing.get("location", "Remote"),
                                                    "description": listing.get("description", "")[:2000],
                                                    "source": "wellfound",
                                                    "url": listing.get("url", "https://wellfound.com/jobs"),
                                                })
                                        except json.JSONDecodeError:
                                            pass
                    except Exception as e:
                        logger.debug(f"Wellfound fallback failed: {e}")

            logger.info(f"✅ Wellfound: {len(jobs)} jobs found")

        except Exception as e:
            logger.warning(f"⚠️ Wellfound failed: {e}")

        return jobs

    async def _search_weworkremotely(self) -> List[Dict]:
        """
        WeWorkRemotely - RSS/JSON API
        
        Programming and DevOps categories for engineering roles.
        """
        logger.info("🔍 Checking WeWorkRemotely...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "VibeJobHunter/1.0"}
                
                # WWR has category-based RSS feeds we can parse
                # Real WWR category slugs (the old "programming"/"devops-sysadmin" 404 now)
                categories = [
                    "remote-programming-jobs",
                    "remote-full-stack-programming-jobs",
                    "remote-back-end-programming-jobs",
                    "remote-devops-sysadmin-jobs",
                    # 2026-08-18: Chief of Staff / Ops-lead / EA-PA roles live here,
                    # not in the engineering categories above. The title filter
                    # below still requires an "ai"/"ml"/"automation"-ish keyword,
                    # so this stays precise rather than admitting generic ops noise.
                    "remote-management-and-finance-jobs",
                ]
                
                for category in categories:
                    url = f"https://weworkremotely.com/categories/{category}.rss"
                    
                    try:
                        async with session.get(url, headers=headers, timeout=15) as resp:
                            if resp.status == 200:
                                xml_text = await resp.text()
                                
                                # Parse RSS XML manually (no external dependency)
                                import re
                                items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
                                
                                for item in items[:20]:
                                    # WWR RSS titles/descriptions are NOT CDATA-wrapped anymore — match both forms
                                    title_match = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item, re.DOTALL)
                                    link_match = re.search(r'<link>(.*?)</link>', item)
                                    desc_match = re.search(r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>', item, re.DOTALL)
                                    
                                    title = title_match.group(1) if title_match else ""
                                    link = link_match.group(1) if link_match else ""
                                    desc = desc_match.group(1) if desc_match else ""
                                    region_match = re.search(r'<region>(.*?)</region>', item)
                                    wwr_region = region_match.group(1).strip() if region_match else "Worldwide"

                                    # Filter for relevant roles
                                    title_lower = title.lower()
                                    if any(kw in title_lower for kw in ["ai", "ml", "engineer", "developer", "programmer", "software", "founding", "senior", "staff", "full stack", "fullstack", "automation"]):
                                        # Extract company from title (format: "Company: Job Title")
                                        parts = title.split(":", 1)
                                        company = parts[0].strip() if len(parts) > 1 else "Remote Company"
                                        job_title = parts[1].strip() if len(parts) > 1 else title
                                        
                                        jobs.append({
                                            "id": f"wwr_{hash(link) % 10000000}",
                                            "title": job_title,
                                            "company": company,
                                            "location": "Remote — " + wwr_region,
                                            "description": desc[:2000],
                                            "source": "weworkremotely",
                                            "url": link,
                                            "remote": True,
                                        })
                    except Exception as e:
                        logger.debug(f"WWR category {category} failed: {e}")

            logger.info(f"✅ WeWorkRemotely: {len(jobs)} jobs found")

        except Exception as e:
            logger.warning(f"⚠️ WeWorkRemotely failed: {e}")

        return jobs

    async def _search_aijobs(self) -> List[Dict]:
        """
        AI-Jobs.net - AI/ML focused job board

        Scrapes the main listings page.

        DORMANT since 2026-08-07 — asleep, not deleted. Set VJH_AIJOBS_ENABLED=true
        to wake it; the scraper below is untouched and still works.

        WHY, measured across all 2,535 postings it has ever returned:
            US            1,003  39.6%
            Europe*       ~980   ~38.7%   (263 tagged + most of 717 German-language)
            Asia/other      431  17.0%
            LATAM           121   4.8%
        and the LATAM slice is country-LOCKED — Brazil, Mexico, Costa Rica — which
        the residency check correctly rejects, because Elena is in Panama.

        Lifetime yield: 2,535 processed → 1 ever surfaced (0.04%). It was not
        producing BAD matches; it was producing correct rejections, every cycle,
        while consuming fetches, ~25s of cycle time and most of the log volume.
        A second independent measurement (the bare-"Remote" recall study, 0 of 30
        fetched would have qualified) reached the same conclusion.

        WAKE IT IF: ai-jobs.net adds a region filter, or Elena's eligibility
        changes (relocation, work authorisation elsewhere).
        """
        import os as _os
        if _os.getenv("VJH_AIJOBS_ENABLED", "false").strip().lower() != "true":
            logger.info("⏭️  AI-Jobs.net: dormant (0.04% lifetime yield; VJH_AIJOBS_ENABLED=true to wake)")
            return []

        logger.info("🔍 Checking AI-Jobs.net...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                }
                
                # Try to get the jobs listing
                url = "https://ai-jobs.net/api/jobs/"
                
                try:
                    async with session.get(url, headers=headers, timeout=15) as resp:
                        if resp.status == 200:
                            try:
                                data = await resp.json()
                                
                                for job in data[:50]:
                                    title = job.get("title", "")
                                    
                                    jobs.append({
                                        "id": f"aijobs_{job.get('id', '')}",
                                        "title": title,
                                        "company": job.get("company", "AI Company"),
                                        "location": job.get("location", "Remote"),
                                        "description": job.get("description", "")[:2000],
                                        "source": "ai_jobs_net",
                                        "url": job.get("url", "https://ai-jobs.net"),
                                        "salary_min": job.get("salary_min"),
                                        "salary_max": job.get("salary_max"),
                                    })
                            except json.JSONDecodeError:
                                # Not JSON, try HTML parsing
                                pass
                except Exception as e:
                    logger.debug(f"AI-Jobs API failed: {e}")
                
                # Fallback: scrape HTML if API doesn't work
                if len(jobs) == 0:
                    try:
                        html_url = "https://ai-jobs.net/"
                        async with session.get(html_url, headers=headers, timeout=15) as resp:
                            if resp.status == 200:
                                html = await resp.text()
                                
                                # Look for job cards in HTML
                                import re
                                
                                # Extract job data from structured data or job cards
                                job_pattern = r'<a[^>]*href="(/job/[^"]+)"[^>]*>([^<]+)</a>'
                                matches = re.findall(job_pattern, html)
                                
                                for link, title in matches[:30]:
                                    if any(kw in title.lower() for kw in ["ai", "ml", "engineer", "machine learning", "data"]):
                                        jobs.append({
                                            "id": f"aijobs_{hash(link) % 10000000}",
                                            "title": title.strip(),
                                            "company": "AI Company",
                                            "location": "Remote",
                                            "description": f"AI/ML role from ai-jobs.net. Full details at https://ai-jobs.net{link}",
                                            "source": "ai_jobs_net",
                                            "url": f"https://ai-jobs.net{link}",
                                        })
                    except Exception as e:
                        logger.debug(f"AI-Jobs HTML scrape failed: {e}")

            logger.info(f"✅ AI-Jobs.net: {len(jobs)} jobs found")

        except Exception as e:
            logger.warning(f"⚠️ AI-Jobs.net failed: {e}")

        return jobs

    # Torre's `locations` array (e.g. ["Argentina","United States","Brazil"]) is a
    # real OR-list of countries the employer accepts candidates from — unlike the
    # single-tag `location` string other sources give. Trust it: if it explicitly
    # names a LATAM country (or Panama), the posting is genuinely open; if it's a
    # non-empty list with NO LATAM country, it's honestly narrow and should be let
    # through to iron_clad_fit's COUNTRY_LOCK check instead of blanket-labeled
    # "LATAM / Americas" regardless of the real data. Empty list = no data from
    # Torre = keep the prior generous default (never worse than before this fix).
    _TORRE_LATAM_COUNTRIES = {
        "panama", "argentina", "brazil", "mexico", "colombia", "chile", "peru",
        "uruguay", "costa rica", "ecuador", "guatemala", "bolivia", "paraguay",
        "venezuela", "dominican republic", "el salvador", "honduras", "nicaragua",
        "belize",
    }

    @classmethod
    def _torre_location_string(cls, locations: List[str]) -> str:
        if not locations:
            # Still "LATAM / Americas" so every gate treats it exactly as before; the mark says it
            # is OUR default, not the employer's statement (src/core/fit_gate.SOURCE_DEFAULT_MARK).
            return f"Remote — LATAM / Americas (Torre default: {SOURCE_DEFAULT_MARK})"
        if any(loc.lower() in cls._TORRE_LATAM_COUNTRIES for loc in locations):
            return f"Remote — Worldwide / LATAM ({', '.join(locations)})"
        return f"Remote — {', '.join(locations)}"

    # Endpoint moved: torre.ai/api 404s now → search.torre.co. Query AI/dev
    # skills; Torre is a LATAM-first remote platform, so results are LATAM-friendly.
    # 2026-07-30: appended AI-automation skills (Torre is the LATAM-first source,
    # so these terms matter most here). Original 5 kept.
    # 2026-08-05: AI-leadership and advisory terms added. Unblocking
    # "Head of AI" at the gate changes nothing if no source is ever
    # ASKED for it — supply has to be searched before it can be judged.
    # These titles also serve the fractional/consulting lane.
    # 2026-10-06: lifted out of the loop unchanged (so tests can read it), minus
    # "ai evaluation" — Elena dropped the expert-AI-evaluation lane on 6 Oct.
    _TORRE_KEYWORDS = (
        "ai engineer", "machine learning", "python developer", "automation engineer", "react developer",
        "ai automation", "ai agents", "workflow automation", "n8n", "zapier",
        "prompt engineering", "ai integration", "no-code",
        "head of ai", "ai consultant", "ai solutions architect",
        "ai product manager", "ai strategy", "fractional cto",
        # 2026-08-05: employers who describe the WORK the way
        # Elena actually works. IgniteTech's board reads "we hire
        # individuals who already think in agents, not just
        # prompts" — a company selecting for exactly her operating
        # style. Its own roles were Java/PMP-gated, but the
        # PHRASING is the signal: find the ones writing like that
        # and not demanding an enterprise stack.
        "ai native", "agent orchestration", "agentic engineer",
        "ai augmented", "forward deployed",
        # 2026-08-18: "Chief of Staff @ Pets Table" (a real posting
        # heavy on AI-driven operational systems + AI marketing
        # integration) was never fetched — no query asked Torre for
        # it. Chief-of-Staff / AI-ops-lead / AI-proficient EA-PA
        # roles fit the same operator-plus-AI-builder profile
        # (7 yrs C-suite + 12 shipped AI systems), including the
        # wealthy-principal/family-office EA-PA lane.
        "ai chief of staff", "chief of staff ai", "ai operations lead",
        "ai executive assistant", "ai personal assistant",
        "ai proficient assistant", "ai proficient executive assistant",
        # 2026-09-16: AI product / consulting / leadership lanes
        # (src/core/target_lanes.py). Torre converts best of all
        # sources, so it gets the widest set of these.
        "chief ai officer", "ai program manager", "technical product manager ai",
        "ai solutions consultant", "ai transformation", "ai implementation manager",
        "ai adoption", "ai enablement", "director of ai", "vp of ai",
        "conversational ai designer", "gtm engineer",
        # 2026-09-28: creative AI lane — Torre is her best-converting source.
        "creative technologist", "generative ai producer", "ai video producer",
        "ai filmmaker", "creative ai", "genai content",
        # 2026-10-06: Professional Outlook (Oct 2026, p.7 "Where I fit") titles not
        # already covered above — AI ops & implementation, AI product &
        # transformation, creative technology.
        "ai implementation lead", "ai workflow architect", "agentic workflow",
        "ai systems operator", "ai innovation lead", "generative ai product lead",
        "ai prototyping", "creative ai pipeline", "ai product automation",
        "genai production",
    )
    _TORRE_SEARCH_URL = "https://search.torre.co/opportunities/_search/?size=20&lang=en"
    # 2026-10-06 — VJH identifies as itself, deliberately. Since 2 Oct 02:56 UTC
    # search.torre.co answers 400 {"meta":{"message":"Invalid request"}} to EVERY
    # body (even {}) unless the User-Agent is Torre's own internal client string;
    # a browser UA gets 400 and python-requests gets 401. That is an access gate
    # added on their side, not a changed payload format. Torre's terms (B.6) forbid
    # "to spider, crawl, or scrape the Content of the Product" and "to interfere
    # with or circumvent the security features", and torre.ai/robots.txt disallows
    # /api/. Borrowing their internal client name to get through would be exactly
    # that, so it is not done here; restoring Torre needs access Torre grants.
    _TORRE_HEADERS = {"User-Agent": "Mozilla/5.0 (VibeJobHunter)", "Content-Type": "application/json"}
    # A 4xx is a deterministic refusal: the same request will be refused again.
    # After this many in a row with nothing answered, stop asking this cycle.
    _TORRE_FAIL_FAST_AFTER = 3

    @staticmethod
    def _torre_payload(kw: str) -> Dict:
        """The opportunity-search body VJH sends (unchanged 2026-10-06 — see _TORRE_HEADERS)."""
        return {"and": [{"skill/role": {"text": kw, "experience": "potential-to-develop"}}]}

    async def _search_torre(self) -> List[Dict]:
        """
        Torre.ai — LATAM-focused tech job platform.
        Explicitly designed for remote work and LATAM talent.
        Uses Torre's public opportunity search API.
        """
        logger.info("🔍 Checking Torre.ai (LATAM)...")
        jobs = []
        seen = set()
        # 2026-10-06: count every refusal. The old loop did `continue` on a non-200 and
        # on any exception, so four days of HTTP 400 logged "✅ Torre.ai: 0 jobs found".
        attempted = failed = answered = refusals_in_a_row = 0
        first_error = ""
        keywords = self._TORRE_KEYWORDS
        try:
            async with aiohttp.ClientSession() as session:
                headers = self._TORRE_HEADERS
                for kw in keywords:
                    if not answered and refusals_in_a_row >= self._TORRE_FAIL_FAST_AFTER:
                        logger.warning(f"   ⚠️ Torre.ai: {refusals_in_a_row} refusals in a row ({first_error}); "
                                       f"{len(keywords) - attempted} searches not sent this cycle")
                        break
                    payload = self._torre_payload(kw)
                    url = self._TORRE_SEARCH_URL
                    attempted += 1
                    try:
                        async with session.post(url, json=payload, headers=headers, timeout=15) as resp:
                            if resp.status != 200:
                                err = _http_error(resp.status, await resp.text())
                                logger.warning(f"   ⚠️ Torre.ai [{kw}]: {err}")
                                failed += 1
                                refusals_in_a_row = refusals_in_a_row + 1 if 400 <= resp.status < 500 else 0
                                first_error = first_error or err
                                continue
                            data = await resp.json()
                        answered += 1
                        refusals_in_a_row = 0
                        results = data.get("results", []) if isinstance(data, dict) else data
                        for opp in (results or []):
                            if not opp.get("remote"):   # remote-only (honest — don't mislabel on-site as remote)
                                continue
                            # CLOSED / EXPIRED (added 2026-07-31). Torre's own API
                            # carries `status` ("open") and `deadline`, and we were
                            # ignoring both — so two already-closed openings reached
                            # Elena's "I Act TODAY" and wasted her clicks. Cheapest
                            # possible place to catch it: before the job even exists.
                            _status = str(opp.get("status", "") or "").lower()
                            if _status and _status != "open":
                                continue
                            _deadline = str(opp.get("deadline", "") or "")
                            if _deadline:
                                try:
                                    _dl = datetime.fromisoformat(_deadline.replace("Z", "+00:00"))
                                    if _dl < datetime.now(timezone.utc):
                                        continue
                                except Exception:
                                    pass  # unparseable deadline → keep the job

                            title = opp.get("objective", "") or opp.get("tagline", "")
                            slug = opp.get("slug") or opp.get("id", "")
                            if not title or slug in seen:
                                continue
                            seen.add(slug)
                            orgs = opp.get("organizations", []) or []
                            company = orgs[0].get("name", "Torre Co") if orgs else "Torre Co"
                            location = self._torre_location_string(opp.get("locations") or [])
                            jobs.append({
                                "id": f"torre_{hash(slug) % 10000000}",
                                "title": title,
                                "company": company,
                                "location": location,
                                "description": (opp.get("tagline", "") or "") + " [Remote role via Torre.ai]",
                                "source": "torre",
                                # Torre's public job page resolves on the opaque `id`, NOT the `slug` —
                                # torre.ai/jobs/{slug} alone 404s to /en/404; torre.ai/jobs/{id} redirects
                                # to the real {id}-{slug} page. Verified live 2026-07-08.
                                "url": f"https://torre.ai/jobs/{opp.get('id', '')}" if opp.get("id") else "https://torre.ai",
                                "remote": True,
                            })
                    except Exception as e:
                        # 2026-10-06: was a bare `continue` — a crash looked like "no results".
                        err = f"{type(e).__name__}: {str(e)[:120]}"
                        logger.warning(f"   ⚠️ Torre.ai [{kw}]: {err}")
                        failed += 1
                        refusals_in_a_row = 0   # a timeout is not a refusal — keep asking
                        first_error = first_error or err
                        continue
        except Exception as e:
            logger.warning(f"⚠️ Torre.ai failed: {e}")
            failed += 1
            attempted = max(attempted, failed)
            first_error = first_error or f"{type(e).__name__}: {str(e)[:120]}"
        self._record_health("torre", failed, attempted, first_error)
        lvl, msg = _source_result_line("Torre.ai", len(jobs), failed, attempted, first_error)
        logger.log(lvl, msg)
        return jobs

    async def _search_himalayas(self) -> List[Dict]:
        """
        Himalayas.app — truly global remote jobs, no location restrictions.
        Has a public jobs RSS/JSON feed filtered by category.
        """
        # 2026-09-29 — THIS SOURCE SEARCHED NOTHING UNTIL TODAY. It called /jobs/api, which ignores `q`
        # and `limit` and returns the 20 newest jobs on the whole site (a Salesforce Specialist, an NDT
        # inspector…), so the lane terms never applied; and it read the link from `url`/`applyUrl`, which
        # Himalayas does not send, so every job got the same URL and id. Found because Elena met an
        # "AI Video Producer" posting on Himalayas that VJH never saw. /jobs/api/search?q= is the real
        # search (one phrase per call, 20 results, ~0.4 s) — the posting ranked 3rd for its own title.
        # The calls run concurrently: safe_fetch drops the WHOLE source on timeout (Torre, 17 Sep).
        logger.info("🔍 Checking Himalayas (search, one query per lane)...")
        queries = (
            "AI automation", "AI solutions architect", "AI product manager", "AI operations",
            "AI consultant", "chief AI officer", "AI chief of staff", "AI executive assistant",
            # 2026-10-06: "AI evaluation" removed — Elena dropped that lane on 6 Oct.
            "generative engine optimization", "AI video producer",
            "creative technologist", "generative AI",
            # 2026-10-06: Professional Outlook (Oct 2026, p.7) titles this list did not
            # cover yet. 24 searches measured 2.1 s live at 4 concurrent (all HTTP 200).
            "AI implementation lead", "AI workflow architect", "agentic workflow",
            "AI systems operator", "AI innovation lead", "generative AI product lead",
            "AI prototyping", "creative AI pipeline", "AI product automation",
            "AI transformation", "AI adoption", "GenAI production",
        )
        url = "https://himalayas.app/jobs/api/search"
        headers = {"User-Agent": "VibeJobHunter/1.0", "Accept": "application/json"}
        seen, jobs, failed = set(), [], 0
        first_error = ""
        batches = None
        sem = asyncio.Semaphore(4)

        async def one(session, q):
            async with sem:
                async with session.get(url, headers=headers, params={"q": q},
                                       timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status != 200:
                        # 2026-10-06: carry the body too — a 429 and a 500 need different fixes.
                        raise RuntimeError(_http_error(resp.status, await resp.text()))
                    data = await resp.json()
                    return data.get("jobs", []) if isinstance(data, dict) else []

        try:
            async with aiohttp.ClientSession() as session:
                batches = await asyncio.gather(*(one(session, q) for q in queries), return_exceptions=True)
            for q, batch in zip(queries, batches):
                if isinstance(batch, Exception):
                    # 2026-10-06: was counted but never shown — say which search failed and why.
                    err = str(batch) if isinstance(batch, RuntimeError) else f"{type(batch).__name__}: {str(batch)[:120]}"
                    logger.warning(f"   ⚠️ Himalayas [{q}]: {err}")
                    failed += 1
                    first_error = first_error or err
                    continue
                for item in batch:
                    title = item.get("title", "")
                    job_url = item.get("applicationLink") or item.get("guid") or ""
                    if not title or not job_url or job_url in seen:
                        continue
                    seen.add(job_url)
                    # The real restriction, not a blanket "worldwide". Himalayas tags can be wrong (it
                    # labelled that video job "Mexico only"; the recruiter's own page lists Panama), so
                    # the description says so and the gates judge the posting text.
                    where = [str(x) for x in (item.get("locationRestrictions") or []) if x]
                    location = f"Remote ({', '.join(where)})" if where else "Remote / Worldwide"
                    tag = (f"[Himalayas location tag: {', '.join(where)} — tags are sometimes wrong; check the employer's page]"
                           if where else "[Himalayas: no location restriction listed]")
                    desc = item.get("description") or item.get("excerpt") or ""
                    jobs.append({
                        "id": f"himalayas_{hashlib.md5(job_url.encode()).hexdigest()[:12]}",
                        "title": title,
                        "company": item.get("companyName") or "Remote Co",
                        "location": location,
                        "description": f"{str(desc)[:1500]} {tag}",
                        "source": "himalayas",
                        "url": job_url,
                        "remote": True,
                        "remote_allowed": True,
                    })
        except Exception as e:
            logger.warning(f"⚠️ Himalayas failed: {e}")
            # 2026-10-06: count it. If the session died before the searches came back,
            # none of them was answered; otherwise one batch broke while parsing.
            failed = len(queries) if batches is None else min(failed + 1, len(queries))
            first_error = first_error or f"{type(e).__name__}: {str(e)[:120]}"
        self._record_health("himalayas", failed, len(queries), first_error, unit="searches")
        lvl, msg = _source_result_line("Himalayas", len(jobs), failed, len(queries), first_error, unit="searches")
        logger.log(lvl, msg)
        return jobs

    # ------------------------------------------------------------------
    # Puente Talent Partners (added 2026-10-06)
    # ------------------------------------------------------------------
    # A selective placement network that ONLY hires from Latin America into remote
    # US roles, paid monthly in USD — her exact market, with pay stated on almost
    # every listing (49/53 on 6 Oct; the rest go through salary_gate as unknown),
    # so salary_gate can apply the $3,000/mo floor instead of guessing.
    # Elena approved the source on 6 Oct 2026.
    #
    # Checked before building (6 Oct): robots.txt reads "User-Agent: * / Allow: /"
    # (only /apply/continue is disallowed) and the terms forbid scraping only
    # "except as permitted by its robots policy". The terms also say "You may not
    # reproduce or republish substantial portions of the site" — VJH does neither;
    # it reads the roles for Elena's own search. Never touch /apply/.
    #
    # /jobs is server-rendered: each role is <a href="/jobs/<slug>-<id>"> holding a
    # title, a location ("Latin America · Remote" or a country list) and pay
    # ("$3,000 - $4,000 / month"). Each role page carries the publisher's own
    # schema.org JobPosting JSON-LD (description, applicantLocationRequirements,
    # baseSalary) — read that rather than the hashed CSS-module markup.
    _PUENTE_BASE = "https://puentetalent.com"
    _PUENTE_HEADERS = {"User-Agent": "VibeJobHunter/1.0 (personal job search)", "Accept": "text/html"}
    # Role URL → parsed role page. A role page is fetched ONCE per process; the
    # listing (re-fetched every cycle) decides which roles are still open.
    _PUENTE_PAGE_CACHE: Dict[str, Dict] = {}
    # When a role says "Latin America" but its page could not be read: Puente's own
    # JSON-LD lists Panama among the 18 countries it places from (verified 6 Oct on
    # /jobs/ai-operations-lead-2660 and /jobs/chief-of-staff-2663), so say so.
    _PUENTE_LATAM_FALLBACK = "incl. Panama: Puente places from 18 Latin American countries"

    @staticmethod
    def _puente_text(fragment: str) -> str:
        """HTML → readable text with one line per paragraph / bullet."""
        import html as _html
        import re as _re
        s = _re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", fragment or "")
        s = _re.sub(r"(?i)<li\b[^>]*>", "\n- ", s)
        s = _re.sub(r"(?i)<br\s*/?>|</(p|li|h[1-6]|div|ul|ol)>", "\n", s)
        s = _html.unescape(_re.sub(r"<[^>]+>", " ", s))
        lines = (" ".join(line.split()) for line in s.split("\n"))
        return "\n".join(line for line in lines if line and line != "-")

    @classmethod
    def _parse_puente_listing(cls, page: str) -> List[Dict]:
        """Every role row on puentetalent.com/jobs → {role_id, url, title, location_text, salary_text}."""
        import html as _html
        import re as _re

        def span(inner: str, name: str) -> str:
            # Class names are CSS-module hashed ("JobsExplorer-module__KdFrfW__title");
            # match only the stable "__title" / "__location" / "__salary" suffix.
            m = _re.search(r'<span[^>]*class="[^"]*__' + name + r'\b[^"]*"[^>]*>(.*?)</span>', inner, _re.S)
            return " ".join(_html.unescape(_re.sub(r"<[^>]+>", " ", m.group(1))).split()) if m else ""

        rows, seen_ids = [], set()
        for m in _re.finditer(r'<a\b[^>]*\bhref="(/jobs/[a-z0-9-]+?-(\d+))"[^>]*>(.*?)</a>', page or "", _re.S | _re.I):
            path, role_id, inner = m.group(1), m.group(2), m.group(3)
            title = span(inner, "title")
            if not title or role_id in seen_ids:
                continue
            seen_ids.add(role_id)
            rows.append({
                "role_id": role_id,
                "url": cls._PUENTE_BASE + path,
                "title": title,
                "location_text": span(inner, "location"),
                "salary_text": span(inner, "salary"),
            })
        return rows

    @staticmethod
    def _puente_cut_boilerplate(text: str) -> str:
        """Drop Puente's own pitch from a role description: everything from the
        "Why Puente" heading on (the network's stats, its hiring steps, "Apply now").

        2026-10-06: 51 of the 53 live JSON-LD descriptions fetched 6 Oct carried it
        (the visible page repeats it). It says nothing about the role, yet reads like
        role facts ("a recruiter interview", "the short skills assessment") to anything
        that reads the full text. It sat past char 1,500 in all 51, so the LLM judge's
        window never reached it; iron_clad_fit reads the whole description. Cutting it
        changed JobGate and iron_clad_fit for 0 of those 53 roles."""
        cut = (text or "").find("\nWhy Puente\n")
        # cut > 0, never 0: a description that is ONLY boilerplate stays as it was
        # rather than becoming "" (an empty description holds the role back).
        return (text[:cut] if cut > 0 else (text or "")).strip()

    @classmethod
    def _parse_puente_detail(cls, page: str) -> Dict:
        """A role page → {description, countries, salary_text, date_posted, employment_type}.

        Reads the page's own schema.org JobPosting JSON-LD; falls back to
        <section id="description-panel"> if that block is ever missing. Either way the
        description is cut before "Why Puente" (_puente_cut_boilerplate)."""
        import re as _re
        out = {"description": "", "countries": [], "salary_text": "",
               "date_posted": "", "employment_type": ""}
        for m in _re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page or "", _re.S):
            try:
                data = json.loads(m.group(1))
            except Exception:
                continue
            if isinstance(data, list):
                nodes = data
            elif isinstance(data, dict):
                nodes = data.get("@graph") or [data]
            else:
                continue
            for d in nodes:
                if not isinstance(d, dict) or d.get("@type") != "JobPosting":
                    continue
                out["description"] = cls._puente_cut_boilerplate(cls._puente_text(d.get("description") or ""))
                out["countries"] = [str(c.get("name")).strip() for c in (d.get("applicantLocationRequirements") or [])
                                    if isinstance(c, dict) and c.get("name")]
                out["date_posted"] = str(d.get("datePosted") or "")
                out["employment_type"] = str(d.get("employmentType") or "")
                base = d.get("baseSalary") if isinstance(d.get("baseSalary"), dict) else {}
                val = base.get("value") if isinstance(base.get("value"), dict) else {}
                try:
                    lo = float(val["minValue"]) if val.get("minValue") is not None else None
                    hi = float(val["maxValue"]) if val.get("maxValue") is not None else None
                except (TypeError, ValueError):
                    lo = hi = None
                unit = str(val.get("unitText") or "").lower()
                if (lo or hi) and unit:
                    rng = f"${lo:,.0f} - ${hi:,.0f}" if lo and hi and lo != hi else f"${(lo or hi):,.0f}"
                    out["salary_text"] = f"{rng} / {unit}"
                return out
        # Fallback: the visible description tab (<section id="description-panel">),
        # cut before the same "Why Puente" boilerplate.
        panel = _re.search(r'(?is)<section\b[^>]*\bid="description-panel"[^>]*>(.*?)</section>', page or "")
        if panel:
            out["description"] = cls._puente_cut_boilerplate(cls._puente_text(panel.group(1)))
        return out

    @classmethod
    def _puente_location(cls, location_text: str, countries: List[str]) -> str:
        """Location string the gates can judge.

        The page's own country list (JSON-LD) is the employer's statement, so it is
        always written out as a roster in parentheses — fit_gate.roster_excludes_home
        then parks a role whose list omits Panama ("Brazil, Argentina, Colombia,
        Chile") and passes one that names it."""
        region = (location_text or "").replace("· Remote", "").replace("·", " ").strip()
        latam = "latin america" in region.lower()
        if countries:
            # 2026-10-06: home country FIRST, the rest of the roster unchanged.
            # llm_judge.judge_fit shows the judge only location[:80], and Puente's
            # JSON-LD lists Panama 12th of 18 — on the 53 live roles fetched 6 Oct,
            # 0 had Panama inside those 80 chars. The judge was reading a roster
            # without her country: the 28 Sep "LATAM may exclude Panama" veto shape.
            # Only the order moves; fit_gate reads the whole roster either way, and
            # a roster without Panama is still written (and parked) as it was.
            import unicodedata as _ud
            from src.core.fit_gate import HOME_COUNTRY

            def _fold(s: str) -> str:   # "Panamá" == "panama", as fit_gate compares
                return "".join(ch for ch in _ud.normalize("NFKD", s or "")
                               if not _ud.combining(ch)).strip().lower()
            home = _fold(HOME_COUNTRY)
            ordered = ([c for c in countries if _fold(c) == home]
                       + [c for c in countries if _fold(c) != home])
            roster = ", ".join(ordered)
            return f"Remote — Latin America ({roster})" if latam else f"Remote ({roster})"
        if latam:
            return f"Remote — Latin America ({cls._PUENTE_LATAM_FALLBACK})"
        if region and region.lower() != "remote":
            return f"Remote ({region})"
        return "Remote"

    @classmethod
    def _puente_job(cls, row: Dict, detail: Dict) -> Dict:
        """One listing row + its parsed role page → the job dict every source returns."""
        salary = row.get("salary_text") or detail.get("salary_text") or ""
        parts = []
        if salary:
            # First, so the 4,000-char cut downstream can never drop it; in the shape
            # salary_gate parses ("$3,000 - $4,000 / month" → ok, "$350 / month" → below).
            parts.append(f"Salary: {salary} (USD, as listed by Puente).")
        if detail.get("description"):
            parts.append(detail["description"])
        parts.append("[Via Puente Talent Partners, a LATAM-only placement network; "
                     "the hiring company is not named on the listing.]")
        return {
            "id": f"puente_{row['role_id']}",
            "title": row["title"],
            "company": "Puente Talent Partners",
            "location": cls._puente_location(row.get("location_text", ""), detail.get("countries") or []),
            "salary": salary,
            "description": "\n\n".join(parts)[:6000],
            "source": "puente",
            "url": row["url"],
            "remote": True,
            "remote_allowed": True,
        }

    async def _search_puente(self) -> List[Dict]:
        """Puente Talent Partners — every open LATAM-remote role, with its full description."""
        logger.info("🔍 Checking Puente Talent Partners (LATAM placement)...")
        jobs: List[Dict] = []
        try:
            async with aiohttp.ClientSession(headers=self._PUENTE_HEADERS) as session:
                async with session.get(f"{self._PUENTE_BASE}/jobs",
                                       timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    page = await resp.text()
                    if resp.status != 200:
                        err = _http_error(resp.status, page)
                        logger.warning(f"   ⚠️ Puente listing: {err}")
                        self._record_health("puente", 1, 1, err, unit="listing requests")
                        lvl, msg = _source_result_line("Puente", 0, 1, 1, err, unit="listing requests")
                        logger.log(lvl, msg)
                        return jobs
                rows = self._parse_puente_listing(page)
                if not rows:
                    # A 200 page with no role rows means the layout changed — a failure,
                    # never "0 jobs found".
                    err = f"HTTP 200 but 0 role rows parsed from {len(page)} chars (layout changed?)"
                    self._record_health("puente", 1, 1, err, unit="listing requests")
                    lvl, msg = _source_result_line("Puente", 0, 1, 1, err, unit="listing requests")
                    logger.log(lvl, msg)
                    return jobs

                cache = self._PUENTE_PAGE_CACHE
                todo = [r for r in rows if r["url"] not in cache]
                cached = len(rows) - len(todo)
                sem = asyncio.Semaphore(4)
                errors: List[str] = []

                async def fetch(row):
                    async with sem:
                        try:
                            async with session.get(row["url"], timeout=aiohttp.ClientTimeout(total=10)) as r:
                                body = await r.text()
                                if r.status != 200:
                                    return row, _http_error(r.status, body)
                            detail = self._parse_puente_detail(body)
                            if not detail.get("description"):
                                return row, "HTTP 200 but no description found on the role page"
                            cache[row["url"]] = detail   # only successes are cached
                            return row, ""
                        except Exception as e:
                            return row, f"{type(e).__name__}: {str(e)[:120]}"

                for row, err in await asyncio.gather(*(fetch(r) for r in todo)):
                    if err:
                        errors.append(err)
                        if len(errors) <= 5:
                            logger.warning(f"   ⚠️ Puente role page {row['url']}: {err}")
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:120]}"
            logger.warning(f"⚠️ Puente failed: {err}")
            self._record_health("puente", 1, 1, err, unit="listing requests")
            lvl, msg = _source_result_line("Puente", 0, 1, 1, err, unit="listing requests")
            logger.log(lvl, msg)
            return jobs

        # A role whose page failed is HELD BACK, not sent thin: a title-only job can
        # be judged on no description, marked seen and buried for 21 days. Failures
        # are not cached, so it is retried next cycle.
        by_title: Dict[str, Dict] = {}
        for row in rows:
            detail = self._PUENTE_PAGE_CACHE.get(row["url"])
            if not detail:
                continue
            job = self._puente_job(row, detail)
            # Two open roles can share a title ("GTM Engineer" #2680 at $2-3K and #2637
            # at $3.5-4.5K on 6 Oct). VJH dedupes dict jobs on company::title, so only
            # the first would ever be judged — keep the better-paid one explicitly.
            key = job["title"].strip().lower()
            prev = by_title.get(key)
            if prev is None or self._puente_top_pay(job) > self._puente_top_pay(prev):
                by_title[key] = job
        jobs = list(by_title.values())

        self._record_health("puente", len(errors), len(todo), errors[0] if errors else "", unit="role pages")
        lvl, msg = _source_result_line("Puente", len(jobs), len(errors), len(todo),
                                       errors[0] if errors else "", unit="role pages")
        logger.log(lvl, f"{msg} — {len(rows)} roles listed, {len(todo) - len(errors)} role pages "
                        f"fetched, {cached} from cache, {len(errors)} held back for retry")
        return jobs

    @staticmethod
    def _puente_top_pay(job: Dict) -> float:
        """Top of the stated monthly range ("$3,500 - $4,500 / month" → 4500); 0 if none."""
        import re as _re
        nums = [float(n.replace(",", "")) for n in _re.findall(r"\$\s?([\d,]+)", job.get("salary") or "")]
        return max(nums) if nums else 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _search_brightdata_linkedin(self) -> List[Dict]:
        """
        LinkedIn Jobs via BrightData Web Unlocker.

        Uses linkedin.com/jobs/search/ (SSR content for SEO bots, works with Web Unlocker).
        Parses job cards from the SSR HTML, then enriches top 5 gate-passing candidates
        with individual job page fetches for salary, applicant count, and seniority level.

        DORMANT since 2026-08-09 — asleep, not deleted. Set VJH_LINKEDIN_ENABLED=true
        to wake it; everything below is untouched and still works.

        WHY, measured over two days of real intake:
            linkedin.com   170 jobs   169 with an EMPTY description   170 on-site
            torre.ai        17 jobs     0 empty                         0 on-site
            dice.com        14 jobs     0 empty                         0 on-site
        LinkedIn was 83% of everything entering the pipeline and 100% of it was
        unusable: Bengaluru, Shenyang, Munich, Dallas, Vilnius — on-site cities,
        with no description text to judge. Lifetime: 3,565 processed, 0 ever
        surfaced.

        It is also the only PAID source here (BrightData Web Unlocker credits), so
        it was spending money to deliver jobs that cannot pass the geography gate.

        WAKE IT IF: the scraper is changed to request remote-only listings with
        descriptions attached (`f_WT=2` plus real body text), or Elena's location
        constraints change.
        """
        import os
        import re

        if os.getenv("VJH_LINKEDIN_ENABLED", "false").strip().lower() != "true":
            logger.info("⏭️  BrightData LinkedIn: dormant (0 surfaced in 3,565; VJH_LINKEDIN_ENABLED=true to wake)")
            return []

        BD_TOKEN = os.getenv("BRIGHTDATA_API_TOKEN", "")
        BD_ZONE  = os.getenv("BRIGHTDATA_ZONE", "web_unlocker1")

        if not BD_TOKEN or not BD_ZONE:
            logger.info("\u23ed\ufe0f  BrightData LinkedIn: token not configured, skipping")
            return []

        BD_API = "https://api.brightdata.com/request"
        jobs: List[Dict] = []

        # Target queries: Elena's roles only, worldwide remote
        queries = [
            "founding+AI+engineer",
            "fractional+CTO+remote",
            "AI+automation+engineer+remote",
            # 2026-08-18: AI chief-of-staff / AI-proficient EA-PA lane.
            "AI+chief+of+staff+remote",
            "AI+executive+assistant+remote",
        ]

        async def bd_fetch(url: str) -> str:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    BD_API,
                    json={"zone": BD_ZONE, "url": url, "format": "raw"},
                    headers={"Authorization": f"Bearer {BD_TOKEN}", "Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        return ""
                    return await resp.text()

        def parse_job_cards(html: str) -> List[Dict]:
            """Extract job cards from LinkedIn SSR search HTML."""
            found = []

            # Job IDs from data-entity-urn
            ids = re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)"', html)
            # Titles from base-search-card__title h3
            titles = re.findall(r'class="[^"]*base-search-card__title[^"]*"[^>]*>\s*([^<\n]+?)\s*<', html)
            # Companies from base-search-card__subtitle
            companies = re.findall(r'class="[^"]*base-search-card__subtitle[^"]*"[^>]*>[\s\S]*?<a[^>]*>\s*([^<\n]+?)\s*<', html)
            # Locations from job-search-card__location
            locations = re.findall(r'class="[^"]*job-search-card__location[^"]*"[^>]*>\s*([^<\n]+?)\s*<', html)

            for i, job_id in enumerate(ids):
                found.append({
                    "title":    titles[i].strip()    if i < len(titles)    else "",
                    "company":  companies[i].strip() if i < len(companies) else "",
                    "location": locations[i].strip() if i < len(locations) else "Remote",
                    "url":      f"https://www.linkedin.com/jobs/view/{job_id}",
                    "description": "",
                    "source":   "brightdata_linkedin",
                    "remote_allowed": True,
                    "_li_job_id": job_id,
                })
            return found

        def enrich_job_page(html: str, job: Dict) -> Dict:
            """Extract salary, applicant count, seniority from an individual LI job page."""
            app_match = re.search(r'(?:Over\s+)?(\d[\d,]*)\+?\s+applicants?', html, re.IGNORECASE)
            if app_match:
                job["applicant_count"] = int(app_match.group(1).replace(",", ""))

            sen_match = re.search(r'Seniority level</[^>]+>\s*<[^>]+>\s*([^<]+)', html, re.IGNORECASE)
            if sen_match:
                job["seniority_level"] = sen_match.group(1).strip()

            sal_match = re.search(r'\$(\d[\d,]+)\s*(?:/yr|/year|annually)?\s*[\u2013-]\s*\$(\d[\d,]+)', html)
            if sal_match:
                job["salary_min"] = int(sal_match.group(1).replace(",", ""))
                job["salary_max"] = int(sal_match.group(2).replace(",", ""))

            desc_match = re.search(
                r'<div[^>]*(?:description__text|show-more-less-html)[^>]*>([\s\S]{100,5000}?)</div>',
                html, re.IGNORECASE
            )
            if desc_match:
                raw = desc_match.group(1)
                job["description"] = re.sub(r'<[^>]+>', ' ', raw).strip()[:3000]

            return job

        for query in queries:
            url = (
                f"https://www.linkedin.com/jobs/search/?keywords={query}"
                f"&location=Worldwide&f_WT=2&f_JT=F&f_TPR=r86400"
            )
            try:
                html = await bd_fetch(url)
                if html and len(html) > 1000:
                    cards = parse_job_cards(html)
                    jobs.extend(cards)
                    logger.info(f"   BrightData LI [{query}]: {len(cards)} cards")
                else:
                    logger.warning(f"   BrightData LI [{query}]: empty response ({len(html)} chars)")
            except Exception as e:
                logger.warning(f"   \u26a0\ufe0f  BrightData LI search failed [{query}]: {e}")

            await asyncio.sleep(2)

        if not jobs:
            logger.info("   BrightData LinkedIn: 0 results from search")
            return []

        seen_ids: set = set()
        unique_jobs = []
        for j in jobs:
            jid = j.get("_li_job_id", "")
            if jid and jid not in seen_ids:
                seen_ids.add(jid)
                unique_jobs.append(j)
        jobs = unique_jobs

        # Pre-filter on title before paying for page enrichment
        QUICK_SKIP = [
            "senior software", "staff engineer", "principal engineer",
            "director", "vp ", "vice president", "manager",
        ]
        candidate_jobs = [j for j in jobs if not any(kw in j.get("title","").lower() for kw in QUICK_SKIP)]
        logger.info(f"   BrightData LI: {len(jobs)} unique \u2192 {len(candidate_jobs)} for page enrichment")

        enriched = 0
        for job in candidate_jobs[:5]:
            jid = job.get("_li_job_id", "")
            if not jid:
                continue
            try:
                page_html = await bd_fetch(f"https://www.linkedin.com/jobs/view/{jid}")
                if page_html and len(page_html) > 1000:
                    job = enrich_job_page(page_html, job)
                    enriched += 1
            except Exception as e:
                logger.warning(f"   \u26a0\ufe0f  BrightData LI page [{jid}]: {e}")
            await asyncio.sleep(1)

        logger.info(f"\u2705 BrightData LinkedIn: {len(jobs)} jobs, {enriched} enriched")
        return jobs


    def _job_id(self, job: Any) -> str:
        """Generate unique ID for deduplication"""
        if hasattr(job, 'id') and job.id:
            return str(job.id)
        
        if hasattr(job, 'company') and hasattr(job, 'title'):
            company = str(job.company).lower().strip()
            title = str(job.title).lower().strip()
            return f"{company}::{title}"
        
        if isinstance(job, dict):
            company = str(job.get('company', '')).lower().strip()
            title = str(job.get('title', '')).lower().strip()
            return f"{company}::{title}"
        
        return str(hash(str(job)))

    def _ats_job_to_posting(self, job: Any) -> JobPosting:
        """Convert ATS scraper JobPosting to core JobPosting"""
        return JobPosting(
            id=getattr(job, 'id', ''),
            title=getattr(job, 'title', ''),
            company=getattr(job, 'company', ''),
            location=getattr(job, 'location', 'Remote'),
            description=getattr(job, 'description', ''),
            source=JobSource.OTHER,
            url=getattr(job, 'url', ''),
            posted_date=getattr(job, 'posted_date', datetime.utcnow()),
            remote_allowed=getattr(job, 'remote_allowed', True),
            requirements=getattr(job, 'requirements', []),
            responsibilities=getattr(job, 'responsibilities', []),
        )

    def _dict_to_job_posting(self, job: Dict) -> JobPosting:
        """Convert dict to JobPosting.

        2026-09-01 — `dict.get(key, default)` returns the default only when the key is
        ABSENT. Several public job APIs emit the key present and explicitly null, so
        `{"company": None}` sailed through `.get("company", "")` as None and pydantic
        rejected it, taking the WHOLE cycle down for one malformed record.

        It had been latent for months: those records always sat beyond the max_results
        cap, so nothing ever converted them. Round-robin interleaving (30 Aug) made every
        source reachable, which is what exposed it. Coerce every field explicitly —
        a missing key and a null key must behave the same.
        """
        def _s(key: str, fallback: str = "") -> str:
            v = job.get(key)
            return v.strip() if isinstance(v, str) and v.strip() else fallback

        return JobPosting(
            id=_s('id'),
            title=_s('title'),
            company=_s('company'),
            location=_s('location', 'Remote'),
            description=_s('description') or _s('raw_text'),
            source=JobSource.OTHER,
            url=_s('url'),
            posted_date=datetime.utcnow(),
            remote_allowed=True,
            requirements=[],
            responsibilities=[],
        )
