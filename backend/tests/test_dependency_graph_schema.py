import pytest
from pydantic import ValidationError

from app.schemas.dependency_graph import (
    DependencyGraph,
    DependencyGraphNode,
)


def test_creates_empty_dependency_graph():
    graph = DependencyGraph(repository_id="repo-123")

    assert graph.repository_id == "repo-123"
    assert graph.nodes == []
    assert graph.edges == []


def test_creates_file_node():
    node = DependencyGraphNode(
        id="file:src/main.py",
        kind="file",
        file_path="src/main.py",
    )

    assert node.kind == "file"
    assert node.symbol is None


def test_rejects_file_node_with_symbol():
    with pytest.raises(ValidationError):
        DependencyGraphNode(
            id="file:src/main.py",
            kind="file",
            file_path="src/main.py",
            symbol={
                "name": "main",
                "kind": "function",
                "file_path": "src/main.py",
                "start_line": 1,
                "end_line": 5,
            },
        )


def test_rejects_empty_repository_id():
    with pytest.raises(ValidationError):
        DependencyGraph(repository_id="")


from app.schemas.source_parser import CodeSymbol


def test_creates_symbol_node():
    symbol = CodeSymbol(
        name="calculate_total",
        kind="function",
        file_path="src/utils.py",
        start_line=10,
        end_line=15,
    )

    node = DependencyGraphNode(
        id="symbol:src/utils.py:calculate_total:10",
        kind="symbol",
        file_path="src/utils.py",
        symbol=symbol,
    )

    assert node.kind == "symbol"
    assert node.symbol == symbol
    assert node.file_path == symbol.file_path


def test_rejects_symbol_node_without_symbol():
    with pytest.raises(ValidationError):
        DependencyGraphNode(
            id="symbol:src/utils.py:calculate_total:10",
            kind="symbol",
            file_path="src/utils.py",
        )


def test_rejects_duplicate_node_ids():
    from app.schemas.dependency_graph import DependencyGraph

    with pytest.raises(ValidationError):
        DependencyGraph(
            repository_id="repo-123",
            nodes=[
                DependencyGraphNode(
                    id="file:src/main.py",
                    kind="file",
                    file_path="src/main.py",
                ),
                DependencyGraphNode(
                    id="file:src/main.py",
                    kind="file",
                    file_path="src/other.py",
                ),
            ],
        )


from app.schemas.dependency import CodeDependency


def test_rejects_edge_referencing_missing_file_node():
    with pytest.raises(ValidationError):
        DependencyGraph(
            repository_id="repo-123",
            nodes=[
                DependencyGraphNode(
                    id="file:src/main.py",
                    kind="file",
                    file_path="src/main.py",
                ),
            ],
            edges=[
                CodeDependency(
                    source_file="src/main.py",
                    target_file="src/missing.py",
                    kind="imports",
                ),
            ],
        )



def test_rejects_edge_referencing_missing_symbol():
    symbol = CodeSymbol(
        name="Dog",
        kind="class",
        file_path="src/animals.py",
        start_line=1,
        end_line=2,
    )

    with pytest.raises(ValidationError):
        DependencyGraph(
            repository_id="repo-123",
            nodes=[
                DependencyGraphNode(
                    id="file:src/animals.py",
                    kind="file",
                    file_path="src/animals.py",
                ),
                DependencyGraphNode(
                    id="symbol:src/animals.py:Dog:1",
                    kind="symbol",
                    file_path="src/animals.py",
                    symbol=symbol,
                ),
            ],
            edges=[
                CodeDependency(
                    source_file="src/animals.py",
                    target_file="src/animals.py",
                    kind="inherits",
                    source_symbol="Dog",
                    target_symbol="MissingAnimal",
                    line_number=2,
                ),
            ],
        )



def test_rejects_duplicate_symbol_nodes():
    symbol = CodeSymbol(
        name="Dog",
        kind="class",
        file_path="src/animals.py",
        start_line=1,
        end_line=3,
    )

    duplicate_symbol = symbol.model_copy()

    with pytest.raises(ValidationError):
        DependencyGraph(
            repository_id="repo-123",
            nodes=[
                DependencyGraphNode(
                    id="symbol:src/animals.py:Dog:1",
                    kind="symbol",
                    file_path="src/animals.py",
                    symbol=symbol,
                ),
                DependencyGraphNode(
                    id="symbol:src/animals.py:Dog:1:duplicate",
                    kind="symbol",
                    file_path="src/animals.py",
                    symbol=duplicate_symbol,
                ),
            ],
        )



def test_rejects_duplicate_graph_edges():
    edge = CodeDependency(
        source_file="src/animals.py",
        target_file="src/animals.py",
        kind="inherits",
        source_symbol="Dog",
        target_symbol="Animal",
        line_number=3,
    )

    with pytest.raises(ValidationError):
        DependencyGraph(
            repository_id="repo-123",
            nodes=[
                DependencyGraphNode(
                    id="file:src/animals.py",
                    kind="file",
                    file_path="src/animals.py",
                ),
                DependencyGraphNode(
                    id="symbol:src/animals.py:Dog:1",
                    kind="symbol",
                    file_path="src/animals.py",
                    symbol=CodeSymbol(
                        name="Dog",
                        kind="class",
                        file_path="src/animals.py",
                        start_line=1,
                        end_line=4,
                    ),
                ),
                DependencyGraphNode(
                    id="symbol:src/animals.py:Animal:6",
                    kind="symbol",
                    file_path="src/animals.py",
                    symbol=CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="src/animals.py",
                        start_line=6,
                        end_line=8,
                    ),
                ),
            ],
            edges=[edge, edge.model_copy()],
        )



def test_rejects_import_edge_with_symbol_endpoints():
    with pytest.raises(ValidationError):
        DependencyGraph(
            repository_id="repo-123",
            nodes=[
                DependencyGraphNode(
                    id="file:src/main.py",
                    kind="file",
                    file_path="src/main.py",
                ),
                DependencyGraphNode(
                    id="file:src/utils.py",
                    kind="file",
                    file_path="src/utils.py",
                ),
            ],
            edges=[
                CodeDependency(
                    source_file="src/main.py",
                    target_file="src/utils.py",
                    kind="imports",
                    source_symbol="main",
                    target_symbol="helper",
                ),
            ],
        )