"""
Count-aware wording helpers.

Relationship findings state an observed count ("1 linked account",
"18 linked accounts"). Rendering that with a hardcoded plural — or with the
"(s)" cop-out ("1 linked account(s)") — is grammatically wrong for one of the
two cases, and that wording is authoritative: it flows from canonical
evidence into the LLM prompt and the narrative contract. These helpers derive
the noun and verb form from the count so the sentence is always correct.
"""

def pluralize(count: int, singular: str, plural: str = "") -> str:
    """Return the noun form matching the count ("account" / "accounts")."""
    if count == 1:
        return singular
    return plural or f"{singular}s"


def was_were(count: int) -> str:
    """Return the verb form matching the count ("was" / "were")."""
    return "was" if count == 1 else "were"


def counted_noun(count: int, singular: str, plural: str = "") -> str:
    """Return "1 linked account"-style counted noun phrases (count + noun)."""
    return f"{count} {pluralize(count, singular, plural)}"
