
from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.symbols.symbol_index import SymbolIndex
from app.services.symbols.symbol_resolver import resolve_symbol


def make_symbol(name: str, file_path: str) -> CodeSymbol:
    return CodeSymbol(
        name=name,
        kind="class",
        file_path=file_path,
        start_line=1,
        end_line=5,
    )


def make_index(*symbols: CodeSymbol) -> SymbolIndex:
    results = [
        ParseResult(
            file_path=symbol.file_path,
            language="python",
            status="success",
            symbols=[symbol],
        )
        for symbol in symbols
    ]
    return SymbolIndex(results)


def test_resolves_unique_symbol():
    symbol = make_symbol("UserService", "services/user.py")
    result = resolve_symbol(
        "UserService", "main.py", "", make_index(symbol)
    )

    assert result.status == "resolved"
    assert result.candidates == [symbol]


def test_resolves_explicit_import():
    symbol = make_symbol("UserService", "services/user.py")
    index = make_index(symbol)

    result = resolve_symbol(
        "UserService",
        "services/payment.py",
        "from services.user import UserService",
        index,
    )

    assert result.status == "resolved"
    assert result.candidates == [symbol]


def test_resolves_import_alias():
    symbol = make_symbol("UserService", "services/user.py")
    index = make_index(symbol)

    result = resolve_symbol(
        "User",
        "services/payment.py",
        "from services.user import UserService as User",
        index,
    )

    assert result.status == "resolved"
    assert result.reference_name == "User"
    assert result.candidates == [symbol]


def test_duplicate_names_are_ambiguous():
    first = make_symbol("UserService", "services/user.py")
    second = make_symbol("UserService", "legacy/user.py")
    index = make_index(first, second)

    result = resolve_symbol(
        "UserService", "main.py", "", index
    )

    assert result.status == "ambiguous"
    assert result.candidates == [first, second]


def test_missing_symbol_is_unresolved():
    result = resolve_symbol(
        "MissingService", "main.py", "", make_index()
    )

    assert result.status == "unresolved"
    assert result.candidates == []


def test_missing_import_target_does_not_fall_back():
    unrelated = make_symbol("UserService", "legacy/user.py")
    index = make_index(unrelated)

    result = resolve_symbol(
        "UserService",
        "main.py",
        "from services.user import UserService",
        index,
    )

    assert result.status == "unresolved"
    assert result.candidates == []


def test_resolves_same_package_relative_import(tmp_path):

    package = tmp_path / "services"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")

    symbol = make_symbol("UserService", "services/user.py")
    index = make_index(symbol)

    result = resolve_symbol(
        "UserService",
        "services/payment.py",
        "from .user import UserService",
        index,
    )

    assert result.status == "resolved"
    assert result.candidates == [symbol]


def test_resolves_parent_package_relative_import(tmp_path):
    package = tmp_path / "services"
    nested = package / "payments"
    nested.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (nested / "__init__.py").write_text("", encoding="utf-8")

    symbol = make_symbol("UserService", "services/user.py")
    index = make_index(symbol)

    result = resolve_symbol(
        "UserService",
        "services/payments/processor.py",
        "from ..user import UserService",
        index,
    )

    assert result.status == "resolved"
    assert result.candidates == [symbol]


def test_missing_relative_import_target_does_not_fall_back():
    unrelated = make_symbol("UserService", "legacy/user.py")
    index = make_index(unrelated)

    result = resolve_symbol(
        "UserService",
        "services/payment.py",
        "from .user import UserService",
        index,
    )

    assert result.status == "unresolved"
    assert result.candidates == []




def test_resolves_symbol_in_package_init():
    symbol = make_symbol("UserService", "services/__init__.py")
    index = make_index(symbol)

    result = resolve_symbol(
        "UserService",
        "main.py",
        "from services import UserService",
        index,
    )

    assert result.status == "resolved"
    assert result.candidates == [symbol]


def test_resolves_explicit_module_inside_package():
    symbol = make_symbol("UserService", "services/user.py")
    index = make_index(symbol)

    result = resolve_symbol(
        "UserService",
        "main.py",
        "from services.user import UserService",
        index,
    )

    assert result.status == "resolved"
    assert result.candidates == [symbol]


def test_package_import_does_not_match_unrelated_module():
    unrelated = make_symbol("UserService", "legacy/__init__.py")
    index = make_index(unrelated)

    result = resolve_symbol(
        "UserService",
        "main.py",
        "from services import UserService",
        index,
    )

    assert result.status == "unresolved"
    assert result.candidates == []




def test_resolves_qualified_reference_with_module_alias():
    symbol = make_symbol("UserService", "services/user.py")
    index = make_index(symbol)

    result = resolve_symbol(
        "user.UserService",
        "main.py",
        "import services.user as user",
        index,
    )

    assert result.status == "resolved"
    assert result.candidates == [symbol]


def test_qualified_reference_does_not_match_wrong_module():
    unrelated = make_symbol("UserService", "legacy/user.py")
    index = make_index(unrelated)

    result = resolve_symbol(
        "user.UserService",
        "main.py",
        "import services.user as user",
        index,
    )

    assert result.status == "unresolved"
    assert result.candidates == []


def test_unknown_module_alias_is_unresolved():
    symbol = make_symbol("UserService", "services/user.py")
    index = make_index(symbol)

    result = resolve_symbol(
        "unknown.UserService",
        "main.py",
        "import services.user as user",
        index,
    )

    assert result.status == "unresolved"
    assert result.candidates == []




def test_duplicate_names_without_import_are_ambiguous():
    first = make_symbol("UserService", "services/user.py")
    second = make_symbol("UserService", "legacy/user.py")
    index = make_index(first, second)

    result = resolve_symbol(
        "UserService",
        "main.py",
        "",
        index,
    )

    assert result.status == "ambiguous"
    assert result.candidates == [first, second]


def test_explicit_import_does_not_fall_back_to_unrelated_symbol():
    unrelated = make_symbol("UserService", "legacy/user.py")
    index = make_index(unrelated)

    result = resolve_symbol(
        "UserService",
        "main.py",
        "from services.user import UserService",
        index,
    )

    assert result.status == "unresolved"
    assert result.candidates == []
