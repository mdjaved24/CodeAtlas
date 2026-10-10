
import pytest
from pydantic import ValidationError

from app.schemas.source_parser import CodeSymbol, ParseResult


def test_valid_class_symbol():
    symbol = CodeSymbol(
        name="PaymentService",
        kind="class",
        file_path="src/payments.py",
        start_line=1,
        end_line=5,
    )

    assert symbol.name == "PaymentService"
    assert symbol.parent_name is None


def test_valid_method_has_parent():
    symbol = CodeSymbol(
        name="process_payment",
        kind="method",
        file_path="src/payments.py",
        start_line=2,
        end_line=4,
        parent_name="PaymentService",
    )

    assert symbol.kind == "method"
    assert symbol.parent_name == "PaymentService"


def test_rejects_invalid_line_range():
    with pytest.raises(ValidationError):
        CodeSymbol(
            name="process_payment",
            kind="function",
            file_path="payments.py",
            start_line=10,
            end_line=5,
        )


def test_empty_file_can_have_successful_result():
    result = ParseResult(
        file_path="empty.py",
        language="python",
        status="success",
    )

    assert result.symbols == []
    assert result.has_syntax_errors is False
    assert result.diagnostics == []


def test_partial_result_preserves_symbols_and_diagnostics():
    symbol = CodeSymbol(
        name="valid_function",
        kind="function",
        file_path="broken.py",
        start_line=1,
        end_line=3,
    )

    result = ParseResult(
        file_path="broken.py",
        language="python",
        status="partial",
        symbols=[symbol],
        has_syntax_errors=True,
        diagnostics=["Syntax error detected near line 5"],
    )

    assert len(result.symbols) == 1
    assert result.has_syntax_errors is True
    assert result.status == "partial"


def test_rejects_unknown_symbol_kind():
    with pytest.raises(ValidationError):
        CodeSymbol(
            name="PaymentService",
            kind="variable",
            file_path="payments.py",
            start_line=1,
            end_line=5,
        )
