
from app.services.parsers.javascript_parser import parse_javascript_source


def test_extracts_class_method_and_function():
    source = """
class PaymentService {
    processPayment() {}
}

function calculateTotal() {}
"""

    result = parse_javascript_source(source, "src/payments.js")

    assert result.status == "success"
    assert {
        (symbol.name, symbol.kind)
        for symbol in result.symbols
    } == {
        ("PaymentService", "class"),
        ("processPayment", "method"),
        ("calculateTotal", "function"),
    }


def test_empty_source_returns_no_symbols():
    result = parse_javascript_source("", "src/empty.js")

    assert result.status == "success"
    assert result.symbols == []
