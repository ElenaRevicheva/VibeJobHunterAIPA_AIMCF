"""
🤝 WARM INTRO QUEUE
Manages personal network contacts for warm introductions.
Tracks who was contacted, when, and through which channel.

Networks:
- Cursor meetup contacts
- Panama ecosystem (ISD, coworking, startup events)
- Online communities (Discord, Twitter, LinkedIn connections)

Uses SQLite (same DB as main app) for persistence across reboots.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

DB_PATH = Path("vibejobhunter.db")

# ════════════════════════════════════════════════════════════
# SCHEMA
# ════════════════════════════════════════════════════════════
CREATE_CONTACTS_TABLE = """
CREATE TABLE IF NOT EXISTS warm_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT,
    role TEXT,
    email TEXT,
    linkedin_url TEXT,
    twitter_handle TEXT,
    network TEXT NOT NULL,
    relationship TEXT,
    notes TEXT,
    added_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_contacted_at TEXT,
    contact_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);
"""

CREATE_WARM_OUTREACH_TABLE = """
CREATE TABLE IF NOT EXISTS warm_outreach_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    channel TEXT NOT NULL,
    message_type TEXT,
    message_preview TEXT,
    target_company TEXT,
    target_role TEXT,
    sent_at TEXT NOT NULL DEFAULT (datetime('now')),
    response_received INTEGER DEFAULT 0,
    response_at TEXT,
    response_notes TEXT,
    FOREIGN KEY (contact_id) REFERENCES warm_contacts(id)
);
"""

# ════════════════════════════════════════════════════════════
# NETWORK TYPES
# ════════════════════════════════════════════════════════════
NETWORKS = {
    "cursor_meetup": "Cursor Meetup Contacts",
    "panama_ecosystem": "Panama Ecosystem (ISD, coworking, events)",
    "online_community": "Online Community (Discord, Twitter, etc.)",
    "linkedin_connection": "LinkedIn Connection",
    "conference": "Conference / Event Contact",
    "referral": "Referral from Someone",
    "other": "Other",
}


class WarmIntroQueue:
    """
    Manages warm introduction contacts and outreach.
    
    - Add contacts from your personal network
    - Generate personalized warm intro messages
    - Track who was contacted and when
    - Avoid over-contacting (cooldown period)
    """

    COOLDOWN_DAYS = 30  # Don't contact same person more than once per month

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
        stats = self.get_stats()
        logger.info(
            f"🤝 Warm Intro Queue initialized: "
            f"{stats['total_contacts']} contacts, "
            f"{stats['available_today']} available today"
        )

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(CREATE_CONTACTS_TABLE)
            conn.execute(CREATE_WARM_OUTREACH_TABLE)
            conn.commit()
        finally:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # ════════════════════════════════════════════════════════════
    # CONTACT MANAGEMENT
    # ════════════════════════════════════════════════════════════

    def add_contact(
        self,
        name: str,
        network: str,
        company: str = None,
        role: str = None,
        email: str = None,
        linkedin_url: str = None,
        twitter_handle: str = None,
        relationship: str = None,
        notes: str = None,
    ) -> int:
        """Add a contact to the warm intro database. Returns contact ID."""
        if network not in NETWORKS:
            logger.warning(f"Unknown network '{network}', using 'other'")
            network = "other"

        conn = self._conn()
        try:
            cur = conn.execute(
                """INSERT INTO warm_contacts 
                   (name, company, role, email, linkedin_url, twitter_handle, 
                    network, relationship, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, company, role, email, linkedin_url, twitter_handle,
                 network, relationship, notes),
            )
            conn.commit()
            contact_id = cur.lastrowid
            logger.info(f"✅ Added warm contact: {name} ({network}) -> ID {contact_id}")
            return contact_id
        finally:
            conn.close()

    def add_contacts_bulk(self, contacts: List[Dict]) -> int:
        """Add multiple contacts at once. Returns count added."""
        added = 0
        for c in contacts:
            try:
                self.add_contact(**c)
                added += 1
            except Exception as e:
                logger.warning(f"⚠️ Failed to add contact {c.get('name', '?')}: {e}")
        return added

    def get_contacts(self, network: str = None, status: str = "active") -> List[Dict]:
        """Get contacts, optionally filtered by network."""
        conn = self._conn()
        try:
            if network:
                rows = conn.execute(
                    "SELECT * FROM warm_contacts WHERE network = ? AND status = ? ORDER BY name",
                    (network, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM warm_contacts WHERE status = ? ORDER BY network, name",
                    (status,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ════════════════════════════════════════════════════════════
    # OUTREACH QUEUE - WHO TO CONTACT TODAY
    # ════════════════════════════════════════════════════════════

    def get_available_contacts(self, limit: int = 2) -> List[Dict]:
        """
        Get contacts eligible for outreach today.
        Respects cooldown period (COOLDOWN_DAYS).
        Prioritizes: never-contacted > least-recently-contacted.
        """
        cutoff = (datetime.utcnow() - timedelta(days=self.COOLDOWN_DAYS)).isoformat()

        conn = self._conn()
        try:
            rows = conn.execute(
                """SELECT * FROM warm_contacts 
                   WHERE status = 'active'
                     AND (last_contacted_at IS NULL OR last_contacted_at < ?)
                   ORDER BY 
                     contact_count ASC,
                     last_contacted_at ASC NULLS FIRST
                   LIMIT ?""",
                (cutoff, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def record_outreach(
        self,
        contact_id: int,
        channel: str,
        message_preview: str = None,
        message_type: str = "warm_intro",
        target_company: str = None,
        target_role: str = None,
    ):
        """Record that outreach was sent to a contact."""
        now = datetime.utcnow().isoformat()
        conn = self._conn()
        try:
            # Log the outreach
            conn.execute(
                """INSERT INTO warm_outreach_log
                   (contact_id, channel, message_type, message_preview,
                    target_company, target_role)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (contact_id, channel, message_type, message_preview,
                 target_company, target_role),
            )
            # Update contact record
            conn.execute(
                """UPDATE warm_contacts 
                   SET last_contacted_at = ?, contact_count = contact_count + 1
                   WHERE id = ?""",
                (now, contact_id),
            )
            conn.commit()
            logger.info(f"📝 Recorded warm outreach to contact #{contact_id} via {channel}")
        finally:
            conn.close()

    def record_response(self, contact_id: int, notes: str = None):
        """Record that a contact responded."""
        now = datetime.utcnow().isoformat()
        conn = self._conn()
        try:
            # Update latest outreach for this contact
            conn.execute(
                """UPDATE warm_outreach_log 
                   SET response_received = 1, response_at = ?, response_notes = ?
                   WHERE contact_id = ? 
                     AND id = (SELECT MAX(id) FROM warm_outreach_log WHERE contact_id = ?)""",
                (now, notes, contact_id, contact_id),
            )
            conn.commit()
        finally:
            conn.close()

    # ════════════════════════════════════════════════════════════
    # MESSAGE GENERATION
    # ════════════════════════════════════════════════════════════

    def generate_warm_message(
        self,
        contact: Dict,
        context: str = "general",
        target_company: str = None,
        target_role: str = None,
    ) -> str:
        """
        Generate a warm intro message for a personal network contact.
        These are templates -- Claude enhancement can be added later.
        """
        name = contact.get("name", "there")
        first_name = name.split()[0] if name else "there"
        network = contact.get("network", "other")
        relationship = contact.get("relationship", "")

        # Network-specific openers
        openers = {
            "cursor_meetup": f"Hey {first_name}! Great connecting at the Cursor meetup.",
            "panama_ecosystem": f"Hey {first_name}! Fellow Panama tech scene person here.",
            "online_community": f"Hey {first_name}! We've connected online and I wanted to reach out directly.",
            "linkedin_connection": f"Hi {first_name}, thanks for being connected on LinkedIn.",
            "conference": f"Hi {first_name}! Great meeting you at the event.",
            "referral": f"Hi {first_name}, {relationship or 'a mutual connection'} suggested I reach out.",
            "other": f"Hi {first_name},",
        }

        opener = openers.get(network, openers["other"])

        # Build the ask
        if target_company and target_role:
            ask = (
                f"I noticed you might have connections at {target_company}. "
                f"I'm exploring their {target_role} role and would love a warm intro if you know anyone there."
            )
        elif target_company:
            ask = (
                f"I'm exploring opportunities at {target_company} and saw you might have a connection there. "
                f"Would you be open to making an intro?"
            )
        else:
            ask = (
                "I'm actively looking for Founding Engineer / Senior AI Engineer roles at early-stage AI startups. "
                "If you know anyone hiring or building something interesting, I'd appreciate a pointer."
            )

        message = f"""{opener}

{ask}

Quick context on what I've been building:
- 11 AI products shipped solo in 10 months (7 live with paying users)
- Built 2 AI Co-Founders (CTO + CMO) running autonomously
- Try my live demo: wa.me/50766623757 (EspaLuz Spanish tutor)

No pressure at all -- just thought I'd ask since we're connected. Happy to help with anything on my end too.

Best,
Elena"""

        return message

    # ════════════════════════════════════════════════════════════
    # STATS & REPORTING
    # ════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get warm intro queue statistics."""
        conn = self._conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM warm_contacts WHERE status = 'active'").fetchone()[0]
            
            cutoff = (datetime.utcnow() - timedelta(days=self.COOLDOWN_DAYS)).isoformat()
            available = conn.execute(
                """SELECT COUNT(*) FROM warm_contacts 
                   WHERE status = 'active' 
                     AND (last_contacted_at IS NULL OR last_contacted_at < ?)""",
                (cutoff,),
            ).fetchone()[0]

            total_outreach = conn.execute("SELECT COUNT(*) FROM warm_outreach_log").fetchone()[0]
            responses = conn.execute(
                "SELECT COUNT(*) FROM warm_outreach_log WHERE response_received = 1"
            ).fetchone()[0]

            by_network = {}
            for row in conn.execute(
                "SELECT network, COUNT(*) as cnt FROM warm_contacts WHERE status = 'active' GROUP BY network"
            ).fetchall():
                by_network[row["network"]] = row["cnt"]

            return {
                "total_contacts": total,
                "available_today": available,
                "total_outreach_sent": total_outreach,
                "responses_received": responses,
                "response_rate": f"{responses/total_outreach*100:.0f}%" if total_outreach > 0 else "N/A",
                "by_network": by_network,
            }
        finally:
            conn.close()

    def get_outreach_history(self, limit: int = 20) -> List[Dict]:
        """Get recent warm outreach history."""
        conn = self._conn()
        try:
            rows = conn.execute(
                """SELECT wol.*, wc.name, wc.company as contact_company, wc.network
                   FROM warm_outreach_log wol
                   JOIN warm_contacts wc ON wol.contact_id = wc.id
                   ORDER BY wol.sent_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


# ════════════════════════════════════════════════════════════
# SEED DATA - Initial contacts to populate the queue
# ════════════════════════════════════════════════════════════
SEED_CONTACTS = [
    # ── Cursor Meetup Contacts ──
    # (Add real contacts as you meet them)
    {
        "name": "Cursor Meetup Contact 1",
        "network": "cursor_meetup",
        "relationship": "Met at Cursor meetup",
        "notes": "PLACEHOLDER - Replace with real contacts from meetups",
        "status": "inactive",  # Activate when you add real info
    },
    # ── Panama Ecosystem ──
    {
        "name": "ISD Network Contact 1",
        "network": "panama_ecosystem",
        "relationship": "ISD network",
        "notes": "PLACEHOLDER - Replace with real ISD contacts",
        "status": "inactive",
    },
    # ── Online Community ──
    {
        "name": "AI Discord Contact 1",
        "network": "online_community",
        "relationship": "AI builders Discord",
        "notes": "PLACEHOLDER - Replace with real community contacts",
        "status": "inactive",
    },
]


def seed_contacts_if_empty(queue: WarmIntroQueue):
    """Add placeholder contacts if the database is empty.
    These are inactive by default -- activate them as you fill in real info."""
    stats = queue.get_stats()
    if stats["total_contacts"] == 0:
        logger.info("🌱 Seeding warm contacts with placeholders (inactive until you add real info)")
        conn = queue._conn()
        try:
            for c in SEED_CONTACTS:
                conn.execute(
                    """INSERT INTO warm_contacts 
                       (name, network, relationship, notes, status)
                       VALUES (?, ?, ?, ?, ?)""",
                    (c["name"], c["network"], c.get("relationship"),
                     c.get("notes"), c.get("status", "inactive")),
                )
            conn.commit()
            logger.info(f"🌱 Added {len(SEED_CONTACTS)} placeholder contacts (set status='active' when ready)")
        finally:
            conn.close()
