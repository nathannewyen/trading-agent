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
