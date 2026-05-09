from decimal import Decimal

from django import template

register = template.Library()


@register.filter(name="rupiah")
def rupiah(value):
    """Render an integer / Decimal as `Rp 1.250.000` (id-ID style, no decimals)."""
    if value in (None, ""):
        return "Rp 0"
    try:
        amount = Decimal(value).quantize(Decimal("1"))
    except Exception:
        return "Rp 0"
    sign = "-" if amount < 0 else ""
    n = abs(int(amount))
    formatted = f"{n:,}".replace(",", ".")
    return f"{sign}Rp {formatted}"


@register.filter(name="sub")
def sub(value, arg):
    try:
        return Decimal(value or 0) - Decimal(arg or 0)
    except Exception:
        return 0


@register.filter(name="abs_value")
def abs_value(value):
    try:
        return abs(Decimal(value or 0))
    except Exception:
        return 0


@register.simple_tag
def balance_key(*parts):
    """Build a colon-joined localStorage key for the balance toggle partial.
    UUIDs and other non-strings are stringified safely (the {% add %} filter
    can't concat str+UUID directly)."""
    return ":".join(str(p) for p in parts)


@register.filter(name="rupiah_plain")
def rupiah_plain(value):
    """Render without the Rp prefix (e.g. for input fields)."""
    if value in (None, ""):
        return ""
    try:
        amount = Decimal(value).quantize(Decimal("1"))
    except Exception:
        return ""
    n = abs(int(amount))
    formatted = f"{n:,}".replace(",", ".")
    return formatted
