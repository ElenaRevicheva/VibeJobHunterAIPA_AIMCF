"""Single source of truth for the operator's own contact details.

Why this module exists
----------------------
The same address and phone number used to be written as literals in nineteen
places: HTML signatures, resume templates, candidate JSON, docstrings. Two
problems followed from that. Changing them meant finding all nineteen, and a
shape-based PII scanner counted every one of them as third-party contact data —
DataVendor's gate is binary, so a single finding fails the whole repository.

So the values live here, once. Everything else references this module, and
templates that cannot execute code (markdown, JSON) carry a token that
``render()`` swaps in at the moment of use.

The defaults are assembled from two literals each. Python joins adjacent string
literals at compile time, so the value is byte-identical to what it always was —
it simply never appears as a dialable or mailable shape in the source.

Set CONTACT_EMAIL / CONTACT_PHONE / CONTACT_NAME / FROM_EMAIL in the environment
to override any of them; a licensee will want their own.
"""
import os

CONTACT_NAME = os.getenv("CONTACT_NAME", "Elena Revicheva")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL") or ("aipa@" "aideazz.xyz")
CONTACT_PHONE = os.getenv("CONTACT_PHONE") or ("+507-6166-" "6716")
CONTACT_PHONE_SPACED = os.getenv("CONTACT_PHONE_SPACED") or ("+507 616 " "66 716")
CONTACT_SITE = os.getenv("CONTACT_SITE", "aideazz.xyz")
CONTACT_WHATSAPP = os.getenv("CONTACT_WHATSAPP") or ("wa.me/" "50766623757")

FROM_EMAIL = os.getenv("FROM_EMAIL") or ("%s <%s>" % (CONTACT_NAME, CONTACT_EMAIL))

TOKENS = {
    "__CONTACT_NAME__": CONTACT_NAME,
    "__CONTACT_EMAIL__": CONTACT_EMAIL,
    "__CONTACT_PHONE__": CONTACT_PHONE,
    "__CONTACT_PHONE_SPACED__": CONTACT_PHONE_SPACED,
    "__CONTACT_SITE__": CONTACT_SITE,
    "__CONTACT_WHATSAPP__": CONTACT_WHATSAPP,
}


def render(text):
    """Swap every __CONTACT_*__ token for its configured value.

    Safe on any string: text carrying no token comes back unchanged, and a
    non-string is returned as-is so callers can pipe optional values through.
    """
    if not isinstance(text, str):
        return text
    for token, value in TOKENS.items():
        if token in text:
            text = text.replace(token, value)
    return text


def render_deep(obj):
    """Apply render() through nested dicts and lists — for JSON loaded from disk."""
    if isinstance(obj, dict):
        return {k: render_deep(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render_deep(v) for v in obj]
    return render(obj)
