from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.dependency import CodeDependency
from app.schemas.source_parser import CodeSymbol


GraphNodeKind = Literal["file", "symbol"]


class DependencyGraphNode(BaseModel):
    """A file or code symbol represented in the dependency graph."""

    id: str = Field(min_length=1)
    kind: GraphNodeKind
    file_path: str = Field(min_length=1)
    symbol: CodeSymbol | None = None

    def model_post_init(self, __context: object) -> None:
        if self.kind == "file" and self.symbol is not None:
            raise ValueError("File nodes must not contain a symbol")

        if self.kind == "symbol":
            if self.symbol is None:
                raise ValueError("Symbol nodes must contain a symbol")

            if self.symbol.file_path != self.file_path:
                raise ValueError(
                    "Symbol file_path must match node file_path"
                )


class DependencyGraph(BaseModel):
    """Language-independent dependency graph for one repository."""

    repository_id: str = Field(min_length=1)
    nodes: list[DependencyGraphNode] = Field(default_factory=list)
    edges: list[CodeDependency] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_node_ids(self) -> "DependencyGraph":
        node_ids = [node.id for node in self.nodes]

        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Graph node IDs must be unique")

        return self


    @model_validator(mode="after")
    def validate_edge_files_exist(self) -> "DependencyGraph":
        file_paths = {
            node.file_path
            for node in self.nodes
            if node.kind == "file"
        }

        for edge in self.edges:
            if edge.source_file not in file_paths:
                raise ValueError(
                    f"Edge source file is missing from graph: "
                    f"{edge.source_file}"
                )

            if edge.target_file not in file_paths:
                raise ValueError(
                    f"Edge target file is missing from graph: "
                    f"{edge.target_file}"
                )

        return self


    @model_validator(mode="after")
    def validate_edge_symbols_exist(self) -> "DependencyGraph":
        symbols_by_file = {
            (node.file_path, node.symbol.name)
            for node in self.nodes
            if node.kind == "symbol" and node.symbol is not None
        }

        for edge in self.edges:
            if edge.kind not in (
                "calls",
                "inherits",
                "implements",
                "references",
            ):
                continue

            source = (edge.source_file, edge.source_symbol)
            target = (edge.target_file, edge.target_symbol)

            if source not in symbols_by_file:
                raise ValueError(
                    f"Edge source symbol is missing from graph: {source}"
                )

            if target not in symbols_by_file:
                raise ValueError(
                    f"Edge target symbol is missing from graph: {target}"
                )

        return self


    @model_validator(mode="after")
    def validate_unique_symbol_nodes(self) -> "DependencyGraph":
        symbol_keys = [
            (
                node.file_path,
                node.symbol.name,
                node.symbol.kind,
                node.symbol.start_line,
                node.symbol.end_line,
            )
            for node in self.nodes
            if node.kind == "symbol" and node.symbol is not None
        ]

        if len(symbol_keys) != len(set(symbol_keys)):
            raise ValueError("Graph symbol nodes must be unique")

        return self


    @model_validator(mode="after")
    def validate_unique_edges(self) -> "DependencyGraph":
        edge_keys = [
            (
                edge.source_file,
                edge.target_file,
                edge.kind,
                edge.source_symbol,
                edge.target_symbol,
                edge.line_number,
            )
            for edge in self.edges
        ]

        if len(edge_keys) != len(set(edge_keys)):
            raise ValueError("Graph edges must be unique")

        return self