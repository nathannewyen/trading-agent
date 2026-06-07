import math
import logging

logger = logging.getLogger(__name__)

_SAFE_NAMESPACE = {
    "__builtins__": {},
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
}


def format_currency(value: float, symbol: str = "$") -> str:
    """Return a human-readable currency string, e.g. $1.23B or $456.7M."""
    abs_val = abs(value)
    if abs_val >= 1e12:
        return f"{symbol}{value / 1e12:.2f}T"
    if abs_val >= 1e9:
        return f"{symbol}{value / 1e9:.2f}B"
    if abs_val >= 1e6:
        return f"{symbol}{value / 1e6:.2f}M"
    return f"{symbol}{value:,.2f}"


def format_pct(value: float, decimals: int = 2) -> str:
    """Return a percentage string, e.g. '+12.34%'."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def calculate(expression: str, description: str = "") -> dict:
    try:
        result = eval(expression.strip(), _SAFE_NAMESPACE)  # noqa: S307
        return {
            "description": description,
            "expression": expression,
            "result": round(float(result), 4),
        }
    except Exception as exc:
        logger.error(f"Calculation error for '{expression}': {exc}")
        return {"error": f"Calculation failed: {exc}", "expression": expression}
