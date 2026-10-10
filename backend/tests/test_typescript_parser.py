
from app.services.parsers.typescript_parser import parse_typescript_source


def test_extracts_class_method_and_function():
    source = """
class PaymentService {
    processPayment(): void {}
}

function calculateTotal(): number {
    return 10;
}
"""

    result = parse_typescript_source(source, "src/payments.ts")

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
    result = parse_typescript_source("", "src/empty.ts")

    assert result.status == "success"
    assert result.symbols == []
