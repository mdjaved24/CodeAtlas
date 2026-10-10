
from app.services.parsers.csharp_parser import parse_csharp_source


def test_extracts_class_and_method():
    source = """
class PaymentService
{
    public void ProcessPayment()
    {
    }
}
"""

    result = parse_csharp_source(
        source,
        "src/PaymentService.cs",
    )

    assert result.status == "success"

    assert {
        (symbol.name, symbol.kind)
        for symbol in result.symbols
    } == {
        ("PaymentService", "class"),
        ("ProcessPayment", "method"),
    }


def test_extracts_nested_class():
    source = """
class OuterService
{
    class InnerService
    {
        void Execute()
        {
        }
    }
}
"""

    result = parse_csharp_source(
        source,
        "src/OuterService.cs",
    )

    symbols = {
        (symbol.name, symbol.kind, symbol.parent_name)
        for symbol in result.symbols
    }

    assert ("OuterService", "class", None) in symbols
    assert ("InnerService", "class", "OuterService") in symbols
    assert ("Execute", "method", "InnerService") in symbols


def test_empty_source_returns_no_symbols():
    result = parse_csharp_source(
        "",
        "src/Empty.cs",
    )

    assert result.status == "success"
    assert result.symbols == []
    assert result.has_syntax_errors is False


def test_extracts_interface_struct_enum_and_record():
    source = """
interface IPaymentService
{
    void ProcessPayment();
}

struct PaymentAmount
{
    public decimal Value;
}

enum PaymentStatus
{
    Pending,
    Completed
}

record PaymentRequest(string Id);
"""

    result = parse_csharp_source(
        source,
        "src/PaymentModels.cs",
    )

    assert result.status == "success"

    symbols = {
        (symbol.name, symbol.kind)
        for symbol in result.symbols
    }

    assert ("IPaymentService", "interface") in symbols
    assert ("PaymentAmount", "struct") in symbols
    assert ("PaymentStatus", "enum") in symbols
    assert ("PaymentRequest", "record") in symbols
