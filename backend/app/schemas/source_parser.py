from typing import Literal
from pydantic import BaseModel, Field, model_validator


SymbolKind = Literal[
    "class",
    "function",
    "method",
    "interface",
    "struct",
    "enum",
    "record",
]

ParseStatus = Literal[
    "success",
    "partial",
    "failed",
    "unsupported",
]


class CodeSymbol(BaseModel):
    """A structural symbol extracted from a source file."""

    name: str = Field(min_length=1)
    kind: SymbolKind
    file_path: str = Field(min_length=1)

    # Source locations are 1-based and inclusive.
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)

    # Immediate enclosing class or supported parent scope.
    parent_name: str | None = None

    @model_validator(mode='after')
    def validate_line_range(self):
        if self.start_line>self.end_line:
            raise ValueError(
                "end_line must be greater than or equal to start_line"
            )
        return self



class ParseResult(BaseModel):
    """The outcome of parsing one repository file."""

    file_path: str = Field(min_length=1)
    language: str
    status: ParseStatus

    symbols: list[CodeSymbol] = Field(default_factory=list)

    has_syntax_errors: bool = False
    diagnostics: list[str] = Field(default_factory=list)
