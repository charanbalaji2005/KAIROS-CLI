"""Tests for filesystem tools: read_file with line numbers, write_file, edit_file, apply_patch, delete_file."""

import asyncio
import tempfile
from pathlib import Path

from forge.tools.filesystem import (
    read_file,
    write_file,
    edit_file,
    apply_patch,
    delete_file,
)


def test_read_file_with_line_numbers():
    async def _test():
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "sample.py"
            test_file.write_text("def hello():\n    return 'world'\n\nprint(hello())\n", encoding="utf-8")

            # Full read
            res = await read_file(str(test_file))
            assert "    1 | def hello():" in res
            assert "    2 |     return 'world'" in res
            assert "    4 | print(hello())" in res

            # Sliced read
            sliced = await read_file(str(test_file), start_line=2, end_line=3)
            assert "    2 |     return 'world'" in sliced
            assert "    1 | def hello():" not in sliced

    asyncio.run(_test())


def test_write_and_edit_file():
    async def _test():
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "app.py"

            # Write
            res_write = await write_file(str(test_file), "const timeout = 1000;\n")
            assert "Successfully wrote" in res_write
            assert test_file.exists()

            # Edit exact text
            res_edit = await edit_file(str(test_file), "const timeout = 1000;", "const timeout = 5000;")
            assert "Successfully edited" in res_edit
            assert test_file.read_text(encoding="utf-8") == "const timeout = 5000;\n"

            # Edit text that doesn't exist
            res_missing = await edit_file(str(test_file), "non_existent_text", "foo")
            assert "ERROR: Target old_text not found" in res_missing

    asyncio.run(_test())


def test_apply_patch():
    async def _test():
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "auth.ts"
            test_file.write_text("function authenticate() {\n    const timeout = 1000;\n    return true;\n}\n", encoding="utf-8")

            patch = """
@@ -1,4 +1,4 @@
 function authenticate() {
-    const timeout = 1000;
+    const timeout = 5000;
     return true;
 }
"""
            res = await apply_patch(str(test_file), patch)
            assert "Successfully applied patch" in res
            assert "timeout = 5000" in test_file.read_text(encoding="utf-8")

    asyncio.run(_test())


def test_delete_file():
    async def _test():
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / "trash.txt"
            f.write_text("temporary")
            assert f.exists()

            res = await delete_file(str(f))
            assert "Successfully removed file" in res
            assert not f.exists()

    asyncio.run(_test())
