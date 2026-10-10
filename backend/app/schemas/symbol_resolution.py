from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.source_parser import CodeSymbol


ResolutionStatus = Literal[
    "resolved",
    "ambiguous",
    "unresolved",
]


class SymbolResolution(BaseModel):
    """Outcome of resolving a symbol reference."""

    reference_name: str = Field(min_length=1)
    source_file: str = Field(min_length=1)
    status: ResolutionStatus
    candidates: list[CodeSymbol] = Field(default_factory=list)