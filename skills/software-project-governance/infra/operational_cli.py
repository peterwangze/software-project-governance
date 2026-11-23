"""Small command-line primitives shared by bounded external operations."""




def _resolve_positive_timeout(raw, default):
    """Shared FIX-234-style env-var timeout resolution.

    Positive integer seconds win; absent/invalid values fall back to the
    supplied default (never crashes the caller).
    """
    raw = (raw or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default
