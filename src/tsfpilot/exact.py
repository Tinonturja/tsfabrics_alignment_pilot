"""Exact arithmetic helpers (section 15, "Exact arithmetic"; section 21 boundary rules).

Every decision quantity is a fractions.Fraction or an int. Comparisons with thresholds are made on q9(x):
x rounded half-even to 9 decimal places in a 60-digit decimal context. Floats (bootstrap bounds only) are
converted with their exact binary value first.
"""
from decimal import Decimal, ROUND_HALF_EVEN, Context
from fractions import Fraction

_CTX = Context(prec=60, rounding=ROUND_HALF_EVEN)
_Q = Decimal("1e-9")


def to_decimal(x):
    """Exact Decimal of an int, Fraction, Decimal or float (60 significant digits for non-terminating fractions)."""
    if isinstance(x, Decimal):
        return x
    if isinstance(x, bool):
        raise TypeError("bool is not a number here")
    if isinstance(x, int):
        return Decimal(x)
    if isinstance(x, Fraction):
        return _CTX.divide(Decimal(x.numerator), Decimal(x.denominator))
    if isinstance(x, float):
        if x != x or x in (float("inf"), float("-inf")):
            raise ValueError("non-finite value reached a decision comparison")
        return Decimal(x)          # exact binary value
    raise TypeError(f"unsupported type {type(x).__name__}")


def q9(x):
    """Round half-even to 9 decimal places."""
    return _CTX.quantize(to_decimal(x), _Q)


def D(s):
    """Decimal constant from a string, e.g. D('0.02')."""
    return Decimal(s)


def sign9(x):
    v = q9(x)
    return (v > 0) - (v < 0)


def frac_to_str(x):
    """Serialise a Fraction for JSON as 'num/den'."""
    x = Fraction(x)
    return f"{x.numerator}/{x.denominator}"
