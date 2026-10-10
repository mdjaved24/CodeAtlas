
from collections import defaultdict

from app.schemas.source_parser import CodeSymbol, ParseResult


class SymbolIndex:
    """In-memory index for symbols extracted from repository files."""

    def __init__(self, parse_results: list[ParseResult]) -> None:
        self._by_name: dict[str, list[CodeSymbol]] = defaultdict(list)
        self._by_file: dict[str, list[CodeSymbol]] = defaultdict(list)
        self._by_kind: dict[str, list[CodeSymbol]] = defaultdict(list)

        for result in parse_results:
            # Only index results that were parsed successfully or partially.
            if result.status not in ("success", "partial"):
                continue

            for symbol in result.symbols:
                self._by_name[symbol.name].append(symbol)
                self._by_file[symbol.file_path].append(symbol)
                self._by_kind[symbol.kind].append(symbol)

    def find_by_name(self, name: str) -> list[CodeSymbol]:
        """Return all symbols with the exact name."""
        return list(self._by_name.get(name, []))

    def find_by_file(self, file_path: str) -> list[CodeSymbol]:
        """Return all symbols belonging to the given file."""
        return list(self._by_file.get(file_path, []))

    def find_by_kind(self, kind: str) -> list[CodeSymbol]:
        """Return all symbols matching the given kind."""
        return list(self._by_kind.get(kind, []))

    def __len__(self) -> int:
        """Return the total number of indexed symbols."""
        return sum(len(symbols) for symbols in self._by_name.values())
