"""Tool registry and schema generation for Anthropic, OpenAI, Ollama, and Gemini."""

import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from forge.tools.filesystem import read_file, write_file, edit_file, apply_patch, delete_file
from forge.tools.search import search, glob_files, list_files
from forge.tools.shell import execute_command
from forge.tools.git import git_status, git_diff, git_commit, git_push, git_branch, git_log
from forge.tools.github import gh_pr_create, gh_pr_list, gh_ci_status
from forge.tools.tests import run_tests


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable


class ToolRegistry:
    """Central registry of executable agent tools."""

    def __init__(self, workspace: Optional[str] = None):
        self.workspace = workspace
        self.tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        handler: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registers a function as a tool, generating JSON schema if not provided."""
        tool_name = name or handler.__name__
        tool_desc = description or (inspect.getdoc(handler) or f"Execute {tool_name}").strip()
        schema = parameters or self._extract_schema(handler)

        self.tools[tool_name] = ToolDefinition(
            name=tool_name,
            description=tool_desc,
            parameters=schema,
            handler=handler,
        )

    def _extract_schema(self, func: Callable) -> Dict[str, Any]:
        """Generates a JSON Schema object from a Python function signature."""
        sig = inspect.signature(func)
        properties: Dict[str, Any] = {}
        required: List[str] = []

        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in sig.parameters.items():
            if param_name in ("workspace", "self"):
                continue

            # Determine type
            annotation = param.annotation
            param_type = "string"
            if annotation in type_mapping:
                param_type = type_mapping[annotation]
            elif hasattr(annotation, "__origin__"):
                origin = annotation.__origin__
                if origin in (list, List):
                    param_type = "array"
                elif origin in (dict, Dict):
                    param_type = "object"
                elif str(origin) == "typing.Union":
                    # Handle Optional[X]
                    args = [a for a in annotation.__args__ if a is not type(None)]
                    if args and args[0] in type_mapping:
                        param_type = type_mapping[args[0]]

            prop_def: Dict[str, Any] = {"type": param_type}

            # Check if required
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

            properties[param_name] = prop_def

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def anthropic_schemas(self) -> List[Dict[str, Any]]:
        """Formats tools for Anthropic Claude API."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in self.tools.values()
        ]

    def openai_schemas(self) -> List[Dict[str, Any]]:
        """Formats tools for OpenAI and Ollama APIs."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.tools.values()
        ]

    def schemas(self) -> List[Dict[str, Any]]:
        """Default schemas formatted for tool use."""
        return self.openai_schemas()

    async def execute(self, name: str, **kwargs) -> str:
        """Executes a tool by name with the given arguments."""
        if name not in self.tools:
            return f"ERROR: Unknown tool '{name}'."

        tool = self.tools[name]
        handler = tool.handler

        # Inject workspace if accepted by handler
        sig = inspect.signature(handler)
        if "workspace" in sig.parameters and "workspace" not in kwargs:
            kwargs["workspace"] = self.workspace

        # Filter kwargs to only those accepted by handler
        call_kwargs = {}
        for param_name in sig.parameters:
            if param_name in kwargs:
                call_kwargs[param_name] = kwargs[param_name]

        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(**call_kwargs)
            else:
                result = handler(**call_kwargs)

            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            return f"ERROR executing tool '{name}': {str(e)}"


def create_default_registry(workspace: Optional[str] = None) -> ToolRegistry:
    """Builds and populates a ToolRegistry with all standard Forge tools."""
    registry = ToolRegistry(workspace=workspace)

    # Filesystem tools
    registry.register(
        read_file,
        description="Reads file contents with 1-indexed line numbers. Use this before modifying code.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative or absolute file path"},
                "start_line": {"type": "integer", "description": "Starting line number (1-indexed, default 1)"},
                "end_line": {"type": "integer", "description": "Ending line number (inclusive)"},
            },
            "required": ["path"],
        },
    )

    registry.register(
        write_file,
        description="Creates a new file or completely replaces the contents of an existing file.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target file path"},
                "content": {"type": "string", "description": "Full file content to write"},
            },
            "required": ["path", "content"],
        },
    )

    registry.register(
        edit_file,
        description="Replaces an exact snippet of text in an existing file. Preferred for targeted code changes.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target file path"},
                "old_text": {"type": "string", "description": "Exact text to be replaced (must match uniquely)"},
                "new_text": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    )

    registry.register(
        apply_patch,
        description="Applies a unified diff patch to an existing file.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target file path"},
                "patch_text": {"type": "string", "description": "Unified diff patch starting with @@ hunks"},
            },
            "required": ["path", "patch_text"],
        },
    )

    registry.register(
        delete_file,
        description="Deletes a file or directory.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File or directory path to delete"},
            },
            "required": ["path"],
        },
    )

    # Search tools
    registry.register(
        search,
        description="Searches for text or regex pattern across workspace files (like ripgrep).",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search string or regex"},
                "path": {"type": "string", "description": "Directory or file to search in (default: .)"},
                "case_sensitive": {"type": "boolean", "description": "Case sensitivity"},
                "file_pattern": {"type": "string", "description": "Filename filter glob (e.g. *.py)"},
            },
            "required": ["pattern"],
        },
    )

    registry.register(
        glob_files,
        description="Finds files matching a glob pattern (e.g. '**/*.ts', 'src/**/*.rs').",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (default: *)"},
                "path": {"type": "string", "description": "Search directory root (default: .)"},
            },
            "required": ["pattern"],
        },
    )

    registry.register(
        list_files,
        description="Lists the directory structure as a tree up to a maximum depth.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Root directory path (default: .)"},
                "max_depth": {"type": "integer", "description": "Maximum directory depth (default: 3)"},
            },
        },
    )

    # Shell tool
    registry.register(
        execute_command,
        name="execute_command",
        description="Runs a shell command in the workspace directory (e.g. 'npm install', 'cargo check', 'python main.py').",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command line to execute"},
                "cwd": {"type": "string", "description": "Optional working directory"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 120)"},
            },
            "required": ["command"],
        },
    )

    # Git tools
    registry.register(git_status, description="Returns the current Git status, branch, and uncommitted files.")
    registry.register(
        git_diff,
        description="Shows git diff of unstaged or staged changes.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Optional file path to diff"},
                "staged": {"type": "boolean", "description": "Show staged diff if true"},
            },
        },
    )
    registry.register(
        git_commit,
        description="Stages changes and creates a Git commit.",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Commit message"},
                "add_all": {"type": "boolean", "description": "Stage all modified/untracked files first"},
            },
            "required": ["message"],
        },
    )
    registry.register(
        git_push,
        description="Pushes committed changes to remote repository.",
        parameters={
            "type": "object",
            "properties": {
                "branch": {"type": "string", "description": "Target branch name"},
                "force": {"type": "boolean", "description": "Force push with lease"},
            },
        },
    )
    registry.register(
        git_branch,
        description="Lists Git branches or creates a new branch.",
        parameters={
            "type": "object",
            "properties": {
                "create": {"type": "string", "description": "Name of new branch to create"},
            },
        },
    )
    registry.register(
        git_log,
        description="Shows recent Git commit history.",
        parameters={
            "type": "object",
            "properties": {
                "n": {"type": "integer", "description": "Number of commits (default: 10)"},
            },
        },
    )

    # GitHub tools
    registry.register(
        gh_pr_create,
        description="Creates a GitHub Pull Request using the gh CLI.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Pull Request title"},
                "body": {"type": "string", "description": "Pull Request description"},
                "draft": {"type": "boolean", "description": "Create as draft PR"},
            },
            "required": ["title"],
        },
    )
    registry.register(gh_pr_list, description="Lists open GitHub Pull Requests.")
    registry.register(gh_ci_status, description="Fetches latest GitHub Actions CI status.")

    # Test runner
    registry.register(
        run_tests,
        description="Auto-detects test runner (pytest, npm, cargo, go) and executes test suite.",
        parameters={
            "type": "object",
            "properties": {
                "test_command": {"type": "string", "description": "Explicit test command override"},
                "path": {"type": "string", "description": "Specific test file or path"},
            },
        },
    )

    return registry
