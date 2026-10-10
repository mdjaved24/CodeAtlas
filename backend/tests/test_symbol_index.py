
from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.symbols.symbol_index import SymbolIndex


def make_symbol(
    name: str,
    kind: str,
    file_path: str,
    parent_name: str | None = None,
) -> CodeSymbol:
    return CodeSymbol(
        name=name,
        kind=kind,
        file_path=file_path,
        start_line=1,
        end_line=5,
        parent_name=parent_name,
    )


def make_result(
    file_path: str,
    symbols: list[CodeSymbol],
    status: str = "success",
) -> ParseResult:
    return ParseResult(
        file_path=file_path,
        language="python",
        status=status,
        symbols=symbols,
    )


def test_indexes_symbols_from_multiple_files():
    payment = make_symbol("PaymentService", "class", "payment.py")
    user = make_symbol("UserService", "class", "user.py")

    index = SymbolIndex([
        make_result("payment.py", [payment]),
        make_result("user.py", [user]),
    ])

    assert len(index) == 2
    assert index.find_by_name("PaymentService") == [payment]


def test_finds_same_name_in_different_files():
    first = make_symbol("validate", "function", "payment.py")
    second = make_symbol("validate", "function", "user.py")

    index = SymbolIndex([
        make_result("payment.py", [first]),
        make_result("user.py", [second]),
    ])

    assert index.find_by_name("validate") == [first, second]


def test_finds_symbols_by_file():
    service = make_symbol("PaymentService", "class", "payment.py")
    method = make_symbol(
        "process",
        "method",
        "payment.py",
        parent_name="PaymentService",
    )
    other = make_symbol("UserService", "class", "user.py")

    index = SymbolIndex([
        make_result("payment.py", [service, method]),
        make_result("user.py", [other]),
    ])

    assert index.find_by_file("payment.py") == [service, method]


def test_finds_symbols_by_kind():
    service = make_symbol("PaymentService", "class", "payment.py")
    method = make_symbol("process", "method", "payment.py")

    index = SymbolIndex([
        make_result("payment.py", [service, method]),
    ])

    assert index.find_by_kind("class") == [service]
    assert index.find_by_kind("method") == [method]


def test_failed_results_are_not_indexed():
    symbol = make_symbol("PaymentService", "class", "payment.py")

    index = SymbolIndex([
        make_result("payment.py", [symbol], status="failed"),
    ])

    assert len(index) == 0
    assert index.find_by_name("PaymentService") == []


def test_empty_results_create_empty_index():
    index = SymbolIndex([])

    assert len(index) == 0
    assert index.find_by_name("missing") == []
    assert index.find_by_file("missing.py") == []
    assert index.find_by_kind("class") == []
