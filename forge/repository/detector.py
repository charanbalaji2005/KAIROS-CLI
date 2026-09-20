"""Repository detector: identifies languages, package managers, frameworks, and build tools."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from forge.tools.filesystem import resolve_path


@dataclass
class ProjectInfo:
    languages: List[str] = field(default_factory=list)
    package_managers: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    test_runner: Optional[str] = None
    build_command: Optional[str] = None
    run_command: Optional[str] = None
    entry_point: Optional[str] = None


class RepositoryDetector:
    """Inspects workspace files to infer development environment and project stack."""

    @staticmethod
    def detect(workspace: Optional[str] = None) -> ProjectInfo:
        target_dir = resolve_path(".", workspace)
        info = ProjectInfo()

        languages: Set[str] = set()
        package_managers: Set[str] = set()
        frameworks: Set[str] = set()

        # Check Python
        if (target_dir / "pyproject.toml").exists() or (target_dir / "requirements.txt").exists() or (target_dir / "setup.py").exists():
            languages.add("Python")
            if (target_dir / "poetry.lock").exists():
                package_managers.add("poetry")
            elif (target_dir / "uv.lock").exists():
                package_managers.add("uv")
            else:
                package_managers.add("pip")
            info.test_runner = "pytest"

        # Check Rust
        if (target_dir / "Cargo.toml").exists():
            languages.add("Rust")
            package_managers.add("cargo")
            info.test_runner = "cargo test"
            info.build_command = "cargo build"
            info.run_command = "cargo run"

        # Check JavaScript / TypeScript
        pkg_json = target_dir / "package.json"
        if pkg_json.exists():
            languages.add("JavaScript")
            if (target_dir / "tsconfig.json").exists():
                languages.add("TypeScript")

            if (target_dir / "pnpm-lock.yaml").exists():
                package_managers.add("pnpm")
            elif (target_dir / "yarn.lock").exists():
                package_managers.add("yarn")
            elif (target_dir / "bun.lockb").exists():
                package_managers.add("bun")
            else:
                package_managers.add("npm")

            # Inspect package.json dependencies
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "next" in deps:
                    frameworks.add("Next.js")
                elif "react" in deps:
                    frameworks.add("React")
                if "vue" in deps:
                    frameworks.add("Vue")
                if "express" in deps:
                    frameworks.add("Express")
                if "vitest" in deps:
                    info.test_runner = "vitest"
                elif "jest" in deps:
                    info.test_runner = "jest"
            except Exception:
                pass

        # Check Go
        if (target_dir / "go.mod").exists():
            languages.add("Go")
            package_managers.add("go modules")
            info.test_runner = "go test ./..."
            info.build_command = "go build"

        # Check Java
        if (target_dir / "pom.xml").exists():
            languages.add("Java")
            package_managers.add("maven")
            info.test_runner = "mvn test"
            info.build_command = "mvn compile"
        elif (target_dir / "build.gradle").exists() or (target_dir / "build.gradle.kts").exists():
            languages.add("Java/Kotlin")
            package_managers.add("gradle")
            info.test_runner = "./gradlew test"

        # Key entry point detection
        candidates = [
            "src/main.rs",
            "src/lib.rs",
            "main.py",
            "app.py",
            "src/index.ts",
            "src/main.ts",
            "src/index.js",
            "main.go",
        ]
        for c in candidates:
            if (target_dir / c).exists():
                info.entry_point = c
                break

        info.languages = sorted(list(languages))
        info.package_managers = sorted(list(package_managers))
        info.frameworks = sorted(list(frameworks))

        return info
