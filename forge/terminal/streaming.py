"""Streaming output and live status indicator for Forge."""

from contextlib import contextmanager
from typing import Generator
from rich.console import Console
from rich.status import Status

from forge.terminal.renderer import COLOR_ORANGE, COLOR_ORANGE_DARK

console = Console()


@contextmanager
def live_spinner(description: str = "Thinking...") -> Generator[Status, None, None]:
    """Displays an animated spinner with Forge orange styling."""
    status = console.status(f"[{COLOR_ORANGE}]{description}[/]", spinner="dots", spinner_style=COLOR_ORANGE_DARK)
    status.start()
    try:
        yield status
    finally:
        status.stop()


class StreamPrinter:
    """Prints streaming text tokens smoothly to the terminal."""

    def __init__(self):
        self._started = False

    def write_chunk(self, chunk: str) -> None:
        if not self._started:
            self._started = True
            console.print()
        console.print(chunk, end="", highlight=False)

    def finish(self) -> None:
        if self._started:
            console.print("\n")
            self._started = False
