"""Workspace indexer: lightweight index for fast file discovery and symbol search."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from forge.tools.filesystem import resolve_path
from forge.tools.search import IGNORED_DIRS


class WorkspaceIndexer:
    """Maintains an index of workspace files and declared symbols (functions/classes)."""

    def __init__(self, workspace: Optional[str] = None):
        self.workspace = resolve_path(".", workspace)
        self.files: List[str] = []
        self.symbols: Dict[str, List[str]] = {}  # symbol_name -> [file_rel_path:line]

    def build_index(self) -> None:
        """Walks the workspace and indexes files and top-level definitions."""
        self.files.clear()
        self.symbols.clear()

        # Regex for common function / class declarations
        symbol_re = re.compile(
            r"^(?:def|class|async\s+def|fn|pub\s+fn|struct|enum|interface|type|function|export\s+(?:default\s+)?(?:function|class|const|interface))\s+([A-Za-z0-9_]+)",
            re.MULTILINE,
        )

        for root, dirs, filenames in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for fname in filenames:
                if fname.startswith("."):
                    continue
                ext = Path(fname).suffix.lower()
                if ext not in (".py", ".rs", ".ts", ".js", ".go", ".java", ".c", ".cpp", ".h", ".toml", ".json", ".md"):
                    continue

                full_p = Path(root) / fname
                try:
                    rel_p = str(full_p.relative_to(self.workspace)).replace("\\", "/")
                except ValueError:
                    rel_p = str(full_p).replace("\\", "/")

                self.files.append(rel_p)

                # Symbol scanning for code files
                if ext in (".py", ".rs", ".ts", ".js", ".go", ".java"):
                    try:
                        content = full_p.read_text(encoding="utf-8", errors="ignore")
                        for line_idx, line in enumerate(content.splitlines(), start=1):
                            match = symbol_re.match(line.strip())
                            if match:
                                sym = match.group(1)
                                if sym not in self.symbols:
                                    self.symbols[sym] = []
                                self.symbols[sym].append(f"{rel_p}:{line_idx}")
                    except Exception:
                        pass

    def find_symbol(self, name: str) -> List[str]:
        """Finds definitions matching symbol name."""
        return self.symbols.get(name, [])

    def search_symbols(self, query: str) -> Dict[str, List[str]]:
        """Finds symbols containing the query string."""
        q_lower = query.lower()
        return {
            sym: locs for sym, locs in self.symbols.items() if q_lower in sym.lower()
        }
