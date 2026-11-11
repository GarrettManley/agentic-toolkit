"""Gmail IMAP adapter (app-password auth) — search by Gmail query syntax and trash hits."""

from __future__ import annotations

import imaplib

ALL_MAIL = '"[Gmail]/All Mail"'
SPAM = '"[Gmail]/Spam"'


class GmailMailbox:
    """Thin context-managed IMAP session. Gmail-specific: uses X-GM-RAW search and
    X-GM-LABELS to move to Trash (STORE +\\Trash from All Mail is Gmail's 'delete')."""

    def __init__(self, user: str, app_password: str, host: str = "imap.gmail.com") -> None:
        self._user, self._password, self._host = user, app_password, host
        self._imap: imaplib.IMAP4_SSL | None = None

    def __enter__(self) -> GmailMailbox:
        self._imap = imaplib.IMAP4_SSL(self._host)
        self._imap.login(self._user, self._password)
        return self

    def __exit__(self, *exc) -> None:
        if self._imap is not None:
            try:
                self._imap.logout()
            finally:
                self._imap = None

    def search(self, folder: str, gmail_query: str) -> list[bytes]:
        """Return UIDs in ``folder`` matching a Gmail search string."""
        assert self._imap is not None
        self._imap.select(folder)
        escaped = gmail_query.replace("\\", "\\\\").replace('"', '\\"')
        typ, data = self._imap.uid("SEARCH", "X-GM-RAW", f'"{escaped}"')
        if typ != "OK":
            raise imaplib.IMAP4.error(f"SEARCH failed in {folder}: {data!r}")
        return data[0].split() if data and data[0] else []

    def trash(self, folder: str, uids: list[bytes]) -> None:
        assert self._imap is not None
        self._imap.select(folder)
        for uid in uids:
            self._imap.uid("STORE", uid, "+X-GM-LABELS", "(\\Trash)")
