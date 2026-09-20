"""Tests for search, glob_files, and list_files."""

import asyncio
import tempfile
from pathlib import Path

from forge.tools.search import search, glob_files, list_files


def test_search_and_glob():
    async def _test():
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("def authenticate_user():\n    return True\n", encoding="utf-8")
            (root / "src" / "helper.py").write_text("# No auth here\n", encoding="utf-8")

            # Search
            res = await search("authenticate_user", path=str(root))
            assert "main.py:1" in res
            assert "authenticate_user" in res

            # Glob
            globs = await glob_files("*.py", path=str(root))
            assert "main.py" in globs or "helper.py" in globs

            # List files
            listing = await list_files(path=str(root))
            assert "main.py" in listing

    asyncio.run(_test())
