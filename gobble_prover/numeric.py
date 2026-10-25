import functools
import re
import math_verify
from sympy import Tuple
from sympy.parsing.sympy_parser import convert_xor, parse_expr, rationalize, standard_transformations

CHARSET = re.compile(r"^[0-9 ()+\-*/.^,]+$")


def _finite(x):
    return all(_finite(e) for e in x) if isinstance(x, Tuple) else x.is_finite is True


@functools.lru_cache(maxsize=8192)
def parse_value(v):
    if not CHARSET.match(v):
        return None
    try:
        x = parse_expr(v, transformations=standard_transformations + (convert_xor, rationalize))
        x = Tuple(*x) if isinstance(x, tuple) else x
    except Exception:
        return None
    return x if hasattr(x, "free_symbols") and _finite(x) else None


def same_or_unknown(a, b):
    try:
        if math_verify.verify(a, b, timeout_seconds=20):
            return True
    except Exception:
        pass
    if isinstance(a, Tuple) or isinstance(b, Tuple):
        if not (isinstance(a, Tuple) and isinstance(b, Tuple)) or len(a) != len(b):
            return False
        return all(same_or_unknown(x, y) for x, y in zip(a, b))
    try:
        r = a.equals(b)
        return True if r is None else bool(r)
    except Exception:
        return True


def gate1_distinct(a, b):
    xa, xb = parse_value(a), parse_value(b)
    return xa is not None and xb is not None and not same_or_unknown(xa, xb)


def distinct(menu, a, b):
    if a in menu and b in menu:
        return a != b
    return gate1_distinct(a.replace(",", ""), b.replace(",", ""))
