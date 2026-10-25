"""Shared experimental pricing specification; not an accounting system."""
from datetime import date
from decimal import Decimal, InvalidOperation


def terms(start, end, rate, policy):
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        if first.isoformat() != start or last.isoformat() != end or last <= first:
            raise ValueError('Use ISO dates with return date after start date')
        price = Decimal(str(rate))
        if not price.is_finite() or price <= 0:
            raise ValueError('Rate must be positive, finite, with at most two decimal places')
        # Inspect the exact coefficient before arithmetic: Decimal multiplication
        # uses context precision and can hide fractional minor units in long input.
        digits = list(price.as_tuple().digits)
        exponent = price.as_tuple().exponent + 2
        while digits[-1] == 0:
            digits.pop()
            exponent += 1
        if exponent < 0:
            raise ValueError('Rate has fractional minor units')
        if len(digits) + exponent > 19:
            raise ValueError('Rate exceeds supported range')
        minor = int(''.join(str(digit) for digit in digits)) * (10 ** exponent)
        days = (last - first).days
        total = minor * days
        amount = total
        if not 0 < amount <= 9223372036854775807 or minor > 9223372036854775807:
            raise ValueError('Amount exceeds supported range')
        return minor, amount
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise ValueError('Invalid dates or rate') from exc
