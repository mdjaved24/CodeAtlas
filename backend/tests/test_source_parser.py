
from app.services.source_parser import parse_python_source


def test_extracts_class_method_and_top_level_function():
    source = """class PaymentService:
    def process_payment(self, amount):
        return amount > 0

def refund_payment(payment_id):
    pass
"""

    result = parse_python_source(source, "src/payments.py")

    assert result.status == "success"
    assert result.has_syntax_errors is False

    actual = [
        (s.name, s.kind, s.parent_name, s.start_line, s.end_line)
        for s in result.symbols
    ]

    assert actual == [
        ("PaymentService", "class", None, 1, 3),
        ("process_payment", "method", "PaymentService", 2, 3),
        ("refund_payment", "function", None, 5, 6),
    ]


def test_empty_source_returns_no_symbols():
    result = parse_python_source("", "empty.py")

    assert result.status == "success"
    assert result.symbols == []
    assert result.has_syntax_errors is False


def test_preserves_repository_relative_path():
    result = parse_python_source(
        "def hello():\n    pass\n",
        "src/utils/hello.py",
    )

    assert result.symbols[0].file_path == "src/utils/hello.py"


def test_malformed_source_returns_partial_result():
    source = """def valid_function():
    pass

def broken_function(
"""

    result = parse_python_source(source, "broken.py")

    assert result.status == "partial"
    assert result.has_syntax_errors is True
    assert any(
        symbol.name == "valid_function"
        for symbol in result.symbols
    )
    assert result.diagnostics




def test_nested_function_is_not_misclassified_as_method():
    source = """class PaymentService:
    def process_payment(self):
        def validate_amount():
            return True

        return validate_amount()
"""

    result = parse_python_source(source, "payments.py")

    assert result.status == "success"

    symbols = {symbol.name: symbol for symbol in result.symbols}

    assert symbols["PaymentService"].kind == "class"

    assert symbols["process_payment"].kind == "method"
    assert symbols["process_payment"].parent_name == "PaymentService"

    assert symbols["validate_amount"].kind == "function"
    assert symbols["validate_amount"].parent_name == "process_payment"






def test_nested_class_and_method_have_correct_parents():
    source = """class OuterService:
    class InnerService:
        def execute(self):
            pass
"""

    result = parse_python_source(source, "services.py")

    symbols = {symbol.name: symbol for symbol in result.symbols}

    assert symbols["OuterService"].kind == "class"
    assert symbols["OuterService"].parent_name is None

    assert symbols["InnerService"].kind == "class"
    assert symbols["InnerService"].parent_name == "OuterService"

    assert symbols["execute"].kind == "method"
    assert symbols["execute"].parent_name == "InnerService"
