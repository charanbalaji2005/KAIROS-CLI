"""Task planner: plan formulation, progress tracking, and milestone management."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PlanStep:
    index: int
    description: str
    completed: bool = False
    in_progress: bool = False
    notes: Optional[str] = None


class TaskPlanner:
    """Manages high-level plan steps and tracks progress through execution."""

    def __init__(self):
        self.objective: Optional[str] = None
        self.steps: List[PlanStep] = []

    def set_plan(self, objective: str, step_descriptions: List[str]) -> None:
        self.objective = objective
        self.steps = [
            PlanStep(index=i + 1, description=desc)
            for i, desc in enumerate(step_descriptions)
        ]
        if self.steps:
            self.steps[0].in_progress = True

    def mark_step_completed(self, index: int, notes: Optional[str] = None) -> None:
        for step in self.steps:
            if step.index == index:
                step.completed = True
                step.in_progress = False
                step.notes = notes
            elif step.index == index + 1 and not step.completed:
                step.in_progress = True

    def format_plan_markdown(self) -> str:
        if not self.steps:
            return ""
        lines = [f"### 📋 Plan: {self.objective or 'Current Task'}"]
        for step in self.steps:
            if step.completed:
                box = "[x]"
            elif step.in_progress:
                box = "[▶]"
            else:
                box = "[ ]"
            lines.append(f"- {box} Step {step.index}: {step.description}")
            if step.notes:
                lines.append(f"    *Note: {step.notes}*")
        return "\n".join(lines)
