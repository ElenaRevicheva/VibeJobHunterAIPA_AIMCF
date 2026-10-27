"""The detector never marks Elena's mail as read, and no employer mail can slip past it (27 Oct 2026). Offline.

Read-only audit of 14 days on the live mailboxes: 425/425 INBOX mails were \\Seen and 166/166 Spam mails were
not. The detector opened INBOX read-write and fetched RFC822, which sets \\Seen, so Gmail and Zoho showed nothing
new. The same audit found LinkedIn "Paul / Sofia just messaged you" mails dropped by the "noreply@" skip, eight
of them filed in Gmail Spam, which was never scanned, and a processed-id file loaded as bytes that no str key
could ever match. Sequence-number dedupe let a new mail inherit an old mail's number after any archive.
"""
import asyncio
import email
import os
import tempfile

import src.autonomous.response_detector as rd


class FakeIMAP:
    """Minimal IMAP double. Fails the test on anything that could set \\Seen."""

    def __init__(self, folders):
        self.folders = folders            # {folder: [(uid, raw_bytes), ...]}
        self.current = None
        self.calls = []

    def select(self, mailbox, readonly=False):
        assert readonly, f"select({mailbox}) without readonly=True would let fetches set \\Seen"
        name = mailbox.strip('"')
        self.calls.append(("select", name))
        if name not in self.folders:
            return "NO", [b"no such folder"]
        self.current = name
        return "OK", [str(len(self.folders[name])).encode()]

    def response(self, code):
        return code, [b"7"]

    def uid(self, command, *args):
        cmd = command.upper()
        if cmd == "SEARCH":
            uids = b" ".join(str(u).encode() for u, _ in self.folders[self.current])
            return "OK", [uids]
        if cmd == "FETCH":
            uid, spec = args
            assert "RFC822" not in spec.upper() or "PEEK" in spec.upper(), f"fetch {spec} sets \\Seen"
            assert "BODY[" not in spec.upper(), f"fetch {spec} sets \\Seen (use BODY.PEEK[])"
            u = int(uid)
            for seq, (uu, raw) in enumerate(self.folders[self.current], 1):
                if uu == u:
                    if "INTERNALDATE" in spec.upper():
                        return "OK", [f'{seq} (INTERNALDATE "27-Oct-2026 20:00:00 +0000" UID {u})'.encode()]
                    return "OK", [(f"{seq} (UID {u} BODY[] {{{len(raw)}}}".encode(), raw), b")"]
            return "OK", [None]
        raise AssertionError(f"unexpected uid {command}")

    def fetch(self, *a):
        raise AssertionError("sequence-number fetch: dedupe must use UIDs")

    def search(self, *a):
        raise AssertionError("sequence-number search: dedupe must use UIDs")


def _mail(frm, subject, body="Hi Elena, are you free to talk this week?"):
    m = email.message.EmailMessage()
    m["From"], m["Subject"] = frm, subject
    m["Date"] = email.utils.format_datetime(rd.datetime.now().astimezone())
    m.set_content(body)
    return m.as_bytes()


def _detector(tmp, mailbox="gmail"):
    d = rd.ResponseDetector.__new__(rd.ResponseDetector)
    d._processed_ids_path = os.path.join(tmp, "ids.txt")
    d.processed_email_ids = set()
    d._mailbox_name = mailbox

    async def classify(*_):
        return rd.ResponseType.POSITIVE, 0.9, "test", "reply"

    d._ai_classify = classify
    return d


def test_loader_returns_str_keys_that_lookups_can_match():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "ids.txt")
        open(p, "w").write("1206\ngmail:10849\n")
        d = rd.ResponseDetector.__new__(rd.ResponseDetector)
        d._processed_ids_path = p
        ids = d._load_processed_ids()
        assert "1206" in ids and "gmail:10849" in ids


def test_scan_is_read_only_and_reaches_spam():
    with tempfile.TemporaryDirectory() as tmp:
        d = _detector(tmp)
        d.imap_connection = FakeIMAP({
            "INBOX": [(101, _mail("Ana Recruiter <ana@" "acme.com>", "Interview next week?"))],
            "[Gmail]/Spam": [(5694, _mail("LinkedIn <messaging-digest-noreply@" "linkedin.com>", "Paul just messaged you"))],
        })
        found = asyncio.run(d._scan_current_mailbox(24))
        subjects = sorted(r.subject for r in found)
        assert subjects == ["Interview next week?", "Paul just messaged you"]
        assert ("select", "[Gmail]/Spam") in d.imap_connection.calls


def test_keys_are_uids_not_positions():
    with tempfile.TemporaryDirectory() as tmp:
        d = _detector(tmp)
        assert d._uid_key("INBOX", b"7", b"101") == "gmail:inbox:7:uid101"
        assert d._uid_key("[Gmail]/Spam", b"3", b"5694") == "gmail:spam:3:uid5694"


def test_a_second_scan_judges_nothing_twice():
    with tempfile.TemporaryDirectory() as tmp:
        d = _detector(tmp)
        d.imap_connection = FakeIMAP({"INBOX": [(101, _mail("ana@" "acme.com", "Interview next week?"))],
                                      "[Gmail]/Spam": []})
        assert len(asyncio.run(d._scan_current_mailbox(24))) == 1
        assert len(asyncio.run(d._scan_current_mailbox(24))) == 0


def test_no_50_mail_cap():
    with tempfile.TemporaryDirectory() as tmp:
        d = _detector(tmp)
        d.imap_connection = FakeIMAP({"INBOX": [(i, _mail(f"r{i}@" f"co{i}.com", f"Reply {i}")) for i in range(1, 81)],
                                      "[Gmail]/Spam": []})
        assert len(asyncio.run(d._scan_current_mailbox(24))) == 80


def test_person_messages_pass_both_noreply_filters():
    for s in ("messaging-digest-noreply@" "linkedin.com", "messages-noreply@" "linkedin.com",
              "noreply@" "candidates.workablemail.com"):
        assert not rd._sender_is_blocked(s), s
    assert rd._sender_is_blocked("noreply@" "tradingview.com")        # real noise still blocked
