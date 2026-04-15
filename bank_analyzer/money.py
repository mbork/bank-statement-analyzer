# * Money formatting

# ** Locale constants
# TODO: derive these from the system locale instead of hardcoding

DECIMAL_SEPARATOR = ','
THOUSANDS_SEPARATOR = '\u00a0'  # non-breaking space

# ** Internal helper

def _split_amount(amount: int) -> tuple[str, int, int]:
    """Return (sign, zl, gr) for an integer grosz amount."""
    sign = '-' if amount < 0 else ''
    zl, gr = divmod(abs(amount), 100)
    return sign, zl, gr

# ** Public formatters

def format_amount_csv(amount: int) -> str:
    """Format an integer grosz amount as decimal PLN for CSV export.

    Uses `DECIMAL_SEPARATOR` (no thousands separator in CSV).
    """
    sign, zl, gr = _split_amount(amount)
    return f'{sign}{zl}{DECIMAL_SEPARATOR}{gr:02d}'

def format_amount_ui(amount: int) -> str:
    """Format an integer grosz amount as decimal PLN for UI display.

    Uses `THOUSANDS_SEPARATOR` and `DECIMAL_SEPARATOR`.
    """
    sign, zl, gr = _split_amount(amount)
    zl_str = f'{zl:,}'.replace(',', THOUSANDS_SEPARATOR)
    return f'{sign}{zl_str}{DECIMAL_SEPARATOR}{gr:02d}'
