import pytest
from pydantic import ValidationError

from app.schemas.symbol_resolution import SymbolResolution


def test_accepts_resolved_reference():
    result = SymbolResolution(
        reference_name="UserService",
        source_file="services/payment.py",
        status="resolved",
    )

    assert result.status == "resolved"
    assert result.candidates == []


def test_accepts_ambiguous_reference():
    result = SymbolResolution(
        reference_name="UserService",
        source_file="services/payment.py",
        status="ambiguous",
    )

    assert result.status == "ambiguous"


def test_rejects_invalid_status():
    with pytest.raises(ValidationError):
        SymbolResolution(
            reference_name="UserService",
            source_file="services/payment.py",
            status="unknown",
        )


def test_rejects_empty_reference_name():
    with pytest.raises(ValidationError):
        SymbolResolution(
            reference_name="",
            source_file="services/payment.py",
            status="unresolved",
        )