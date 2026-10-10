from app.services.parsers.java_parser import parse_java_source


def test_extracts_class_and_method():
    source = """
class PaymentService {
    void processPayment() {
    }
}
"""

    result = parse_java_source(source, "src/PaymentService.java")

    assert result.status == "success"
    assert {
        (symbol.name, symbol.kind)
        for symbol in result.symbols
    } == {
        ("PaymentService", "class"),
        ("processPayment", "method"),
    }


def test_extracts_nested_class():
    source = """
class OuterService {
    class InnerService {
        void execute() {
        }
    }
}
"""

    result = parse_java_source(source, "src/OuterService.java")

    symbols = {
        (symbol.name, symbol.kind, symbol.parent_name)
        for symbol in result.symbols
    }

    assert ("OuterService", "class", None) in symbols
    assert ("InnerService", "class", "OuterService") in symbols
    assert ("execute", "method", "InnerService") in symbols


def test_empty_source_returns_no_symbols():
    result = parse_java_source("", "src/Empty.java")

    assert result.status == "success"
    assert result.symbols == []
    assert result.has_syntax_errors is False