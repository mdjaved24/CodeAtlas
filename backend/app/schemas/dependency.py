
from typing import Literal

from pydantic import BaseModel, Field, model_validator


DependencyKind = Literal[
    "imports",
    "calls",
    "inherits",
    "implements",
    "references",
]


class CodeDependency(BaseModel):
    """A dependency relationship discovered in repository source code."""

    source_file: str = Field(min_length=1)
    target_file: str = Field(min_length=1)

    kind: DependencyKind

    # Optional symbol-level information.
    source_symbol: str | None = None
    target_symbol: str | None = None

    # Source line where the relationship was detected.
    line_number: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_dependency(self) -> "CodeDependency":
        if self.kind == "imports":
            if self.source_symbol is not None or self.target_symbol is not None:
                raise ValueError(
                    "Import dependencies must not specify symbol endpoints"
                )

        elif self.kind in ("calls", "inherits", "implements", "references"):
            if not self.source_symbol or not self.target_symbol:
                raise ValueError(
                    "Symbol-level dependencies require source_symbol "
                    "and target_symbol"
                )

        return self
