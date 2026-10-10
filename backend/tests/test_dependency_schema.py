
import pytest
from pydantic import ValidationError

from app.schemas.dependency import CodeDependency


def test_creates_file_import_dependency():
    dependency = CodeDependency(
        source_file="services/payment.py",
        target_file="services/user.py",
        kind="imports",
        line_number=1,
    )

    assert dependency.kind == "imports"
    assert dependency.source_symbol is None


def test_creates_symbol_call_dependency():
    dependency = CodeDependency(
        source_file="services/payment.py",
        target_file="services/user.py",
        kind="calls",
        source_symbol="process_payment",
        target_symbol="validate_user",
        line_number=12,
    )

    assert dependency.source_symbol == "process_payment"
    assert dependency.target_symbol == "validate_user"


def test_rejects_call_without_symbols():
    with pytest.raises(ValidationError):
        CodeDependency(
            source_file="payment.py",
            target_file="user.py",
            kind="calls",
        )


def test_rejects_empty_source_file():
    with pytest.raises(ValidationError):
        CodeDependency(
            source_file="",
            target_file="user.py",
            kind="imports",
        )


def test_rejects_invalid_line_number():
    with pytest.raises(ValidationError):
        CodeDependency(
            source_file="payment.py",
            target_file="user.py",
            kind="imports",
            line_number=0,
        )


def test_rejects_unknown_dependency_kind():
    with pytest.raises(ValidationError):
        CodeDependency(
            source_file="payment.py",
            target_file="user.py",
            kind="uses_magic",
        )
