"""Streaming output and live status indicator for Forge."""

from contextlib import contextmanager
from typing import Generator
from rich.console import Console
from rich.status import Status

import rich._spinners
from forge.terminal.renderer import COLOR_ORANGE, COLOR_ORANGE_DARK, COLOR_ORANGE_LIGHT

console = Console()

# Register custom Kairos robot spinner with blinking eyes, glancing, and giggling
ROBOT_SPINNER_FRAMES = [
    "(●) ⟦•_•⟧ ",
    "(●) ⟦•_•⟧ ",
    "(\\●)⟦•_ ⟧ ",
    "(●/)⟦ _•⟧ ",
    "(●) ⟦-_-⟧ ",
    "(●) ⟦^_‐⟧ ",
    "(*●)⟦>_<⟧* ",
    "(●*)⟦^o^⟧~ ",
    "(*●)⟦>_<⟧* ",
    "(●) ⟦▮>_▮⟧ ",
    "(●) ⟦▮>_▮⟧ ",
]

rich._spinners.SPINNERS["kairos_robot"] = {
    "interval": 130,
    "frames": ROBOT_SPINNER_FRAMES,
}


@contextmanager
def live_spinner(description: str = "Thinking...") -> Generator[Status, None, None]:
    """Displays an animated spinner with Kairos robot mascot eye and giggling animations."""
    status = console.status(
        f"[{COLOR_ORANGE}]{description}[/]",
        spinner="kairos_robot",
        spinner_style=f"bold {COLOR_ORANGE}",
    )
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
