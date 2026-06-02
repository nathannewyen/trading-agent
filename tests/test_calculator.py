import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.calculator import calculate


def test_basic_arithmetic():
    r = calculate("2 + 2", "addition")
    assert r["result"] == 4.0


def test_growth_rate():
    r = calculate("(125.4 - 98.2) / 98.2 * 100", "YoY revenue growth")
    assert abs(r["result"] - 27.6986) < 0.001


def test_division_by_zero():
    r = calculate("1 / 0", "div by zero")
    assert "error" in r


def test_negative_result():
    r = calculate("50 - 100", "delta")
    assert r["result"] == -50.0


def test_float_precision():
    r = calculate("1 / 3", "fraction")
    assert 0.333 < r["result"] < 0.334


def test_sqrt():
    r = calculate("sqrt(144)", "square root")
    assert r["result"] == 12.0


def test_description_preserved():
    r = calculate("10 * 5", "units sold times price")
    assert r["description"] == "units sold times price"
    assert r["expression"] == "10 * 5"


def test_pe_ratio():
    r = calculate("150 / 6.5", "P/E ratio")
    assert abs(r["result"] - 23.0769) < 0.001
