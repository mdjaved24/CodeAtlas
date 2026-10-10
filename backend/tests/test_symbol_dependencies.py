
from pathlib import Path

from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.symbols.symbol_index import SymbolIndex
from app.services.dependencies.symbol_dependency_extractor import (
    extract_python_call_dependencies,
)


def make_symbol(
    name: str,
    kind: str,
    file_path: str,
    start_line: int,
    end_line: int,
    parent_name: str | None = None,
) -> CodeSymbol:
    return CodeSymbol(
        name=name,
        kind=kind,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        parent_name=parent_name,
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


def test_extracts_call_to_unique_function(tmp_path: Path):
    source = """\
def process_payment():
    validate_user()
"""
    source_file = "payment.py"
    symbols = [
        make_symbol("process_payment", "function", source_file, 1, 2),
        make_symbol("validate_user", "function", "users.py", 1, 2),
    ]

    dependencies = extract_python_call_dependencies(
        source_file,
        source,
        make_index(*symbols),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_symbol == "process_payment"
    assert dependencies[0].target_symbol == "validate_user"
    assert dependencies[0].kind == "calls"
    assert dependencies[0].line_number == 2


def test_ignores_unresolved_call():
    source = """\
def process_payment():
    missing_function()
"""
    symbol = make_symbol("process_payment", "function", "payment.py", 1, 2)

    dependencies = extract_python_call_dependencies(
        "payment.py",
        source,
        make_index(symbol),
    )

    assert dependencies == []


def test_ignores_ambiguous_call():
    source = """\
def process_payment():
    validate_user()
"""
    symbols = [
        make_symbol("process_payment", "function", "payment.py", 1, 2),
        make_symbol("validate_user", "function", "users.py", 1, 2),
        make_symbol("validate_user", "function", "legacy/users.py", 1, 2),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py",
        source,
        make_index(*symbols),
    )

    assert dependencies == []


def test_extracts_method_call_inside_class(tmp_path: Path):
    source = """\
class PaymentService:
    def process(self):
        self.validate()
"""
    symbols = [
        make_symbol("PaymentService", "class", "payment.py", 1, 3),
        make_symbol(
            "process", "method", "payment.py", 2, 3,
            parent_name="PaymentService",
        ),
        make_symbol(
            "validate", "method", "payment.py", 4, 5,
            parent_name="PaymentService",
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py",
        source,
        make_index(*symbols),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_symbol == "process"
    assert dependencies[0].target_symbol == "validate"
    assert dependencies[0].kind == "calls"




def test_resolves_self_method_call_with_duplicate_method_names():
    source = """\
class PaymentService:
    def process(self):
        self.validate()

    def validate(self):
        pass

class UserService:
    def validate(self):
        pass
"""
    symbols = [
        make_symbol("PaymentService", "class", "payment.py", 1, 5),
        make_symbol(
            "process", "method", "payment.py", 2, 3,
            parent_name="PaymentService",
        ),
        make_symbol(
            "validate", "method", "payment.py", 4, 5,
            parent_name="PaymentService",
        ),
        make_symbol("UserService", "class", "payment.py", 7, 9),
        make_symbol(
            "validate", "method", "payment.py", 8, 9,
            parent_name="UserService",
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py",
        source,
        make_index(*symbols),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_symbol == "process"
    assert dependencies[0].target_symbol == "validate"
    assert dependencies[0].source_file == "payment.py"
    assert dependencies[0].target_file == "payment.py"


def test_does_not_resolve_self_method_to_another_class():
    source = """\
class PaymentService:
    def process(self):
        self.refund()
"""
    symbols = [
        make_symbol("PaymentService", "class", "payment.py", 1, 3),
        make_symbol(
            "process", "method", "payment.py", 2, 3,
            parent_name="PaymentService",
        ),
        make_symbol(
            "refund", "method", "refund.py", 1, 2,
            parent_name="RefundService",
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py",
        source,
        make_index(*symbols),
    )

    assert dependencies == []




def test_resolves_call_through_explicit_import():
    source = """\
from users import validate_user

def process_payment():
    validate_user()
"""
    symbols = [
        make_symbol(
            "process_payment", "function", "payment.py", 3, 4
        ),
        make_symbol(
            "validate_user", "function", "users.py", 1, 2
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py",
        source,
        make_index(*symbols),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_symbol == "process_payment"
    assert dependencies[0].target_symbol == "validate_user"
    assert dependencies[0].source_file == "payment.py"
    assert dependencies[0].target_file == "users.py"
    assert dependencies[0].kind == "calls"


def test_resolves_call_through_import_alias():
    source = """\
from users import validate_user as validate

def process_payment():
    validate()
"""
    symbols = [
        make_symbol(
            "process_payment", "function", "payment.py", 3, 4
        ),
        make_symbol(
            "validate_user", "function", "users.py", 1, 2
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py",
        source,
        make_index(*symbols),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_symbol == "process_payment"
    assert dependencies[0].target_symbol == "validate_user"
    assert dependencies[0].target_file == "users.py"




def test_resolves_call_through_qualified_module():
    source = """\
import users

def process_payment():
    users.validate_user()
"""
    symbols = [
        make_symbol(
            "process_payment", "function", "payment.py", 3, 4
        ),
        make_symbol(
            "validate_user", "function", "users.py", 1, 2
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py",
        source,
        make_index(*symbols),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_symbol == "process_payment"
    assert dependencies[0].target_symbol == "validate_user"
    assert dependencies[0].target_file == "users.py"


def test_resolves_call_through_module_alias():
    source = """\
import users as user_service

def process_payment():
    user_service.validate_user()
"""
    symbols = [
        make_symbol(
            "process_payment", "function", "payment.py", 3, 4
        ),
        make_symbol(
            "validate_user", "function", "users.py", 1, 2
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py",
        source,
        make_index(*symbols),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_symbol == "process_payment"
    assert dependencies[0].target_symbol == "validate_user"
    assert dependencies[0].target_file == "users.py"





def test_ignores_imported_function_missing_from_symbol_index():
    source = """\
from users import missing_function

def process_payment():
    missing_function()
"""
    symbols = [
        make_symbol(
            "process_payment", "function", "payment.py", 3, 4
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py", source, make_index(*symbols)
    )

    assert dependencies == []


def test_ignores_ambiguous_imported_function():
    source = """\
from users import validate_user

def process_payment():
    validate_user()
"""
    symbols = [
        make_symbol(
            "process_payment", "function", "payment.py", 3, 4
        ),
        make_symbol(
            "validate_user", "function", "users.py", 1, 2
        ),
        make_symbol(
            "validate_user", "function", "users.py", 5, 6
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py", source, make_index(*symbols)
    )

    assert dependencies == []


def test_resolves_imported_function_despite_unrelated_duplicate():
    source = """\
from users import validate_user

def process_payment():
    validate_user()
"""
    symbols = [
        make_symbol(
            "process_payment", "function", "payment.py", 3, 4
        ),
        make_symbol(
            "validate_user", "function", "users.py", 1, 2
        ),
        make_symbol(
            "validate_user", "function", "admin.py", 1, 2
        ),
    ]

    dependencies = extract_python_call_dependencies(
        "payment.py", source, make_index(*symbols)
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_symbol == "process_payment"
    assert dependencies[0].target_symbol == "validate_user"
    assert dependencies[0].target_file == "users.py"
