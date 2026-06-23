# scripts/draft/errors.py
"""Stage 6 drafting exceptions."""


class IncompleteVerdict(Exception):
    """A finding template's required verdict fields are missing/unparseable."""
