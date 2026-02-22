"""Clack-style CLI rendering helpers for SafeAI."""

from __future__ import annotations

import sys

import questionary
from questionary import Style
from rich.console import Console

console = Console(highlight=False)

# ── Unicode glyphs ──────────────────────────────────────────────────
BAR = "│"
DIAMOND_OPEN = "◇"
DIAMOND_FILL = "◆"
TOP = "┌"
BOT = "└"
TEE = "├"
CORNER_TR = "╮"
CORNER_BR = "╯"
DASH = "─"
CHECK = "✓"
SKIP = "─"

# ── Questionary style ──────────────────────────────────────────────
QS = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:cyan"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:green"),
    ]
)

ASCII_ART = r"""
 ____         __      _    ___
/ __/__ _  / _|__  / \  |_ _|
\__ \/ _` || |_ / _ \/ _ \ | |
___) | (_| ||  _|  __/ ___ \| |
|____/\__,_||_|  \___|_/   \_\___|
""".strip("\n")


def _is_interactive() -> bool:
    return sys.stdin.isatty()


# ── Output helpers ──────────────────────────────────────────────────


def banner(version: str) -> None:
    """Print the SafeAI ASCII banner with clack-style framing."""
    console.print(f"[bold cyan]{TOP}[/]   [bold]safeai v{version}[/]")
    console.print(f"[bold cyan]{BAR}[/]")
    for line in ASCII_ART.splitlines():
        console.print(f"[bold cyan]{BAR}[/]   [cyan]{line}[/]")
    console.print(f"[bold cyan]{BAR}[/]")
    console.print(
        f"[bold cyan]{BAR}[/]  [dim]Framework-agnostic runtime boundary enforcement for AI systems[/]"
    )
    console.print(f"[bold cyan]{BAR}[/]")


def bar(text: str = "", style: str = "") -> None:
    """Print a connector bar line."""
    if text:
        if style:
            console.print(f"[bold cyan]{BAR}[/]  [{style}]{text}[/]")
        else:
            console.print(f"[bold cyan]{BAR}[/]  {text}")
    else:
        console.print(f"[bold cyan]{BAR}[/]")


def step_active(label: str) -> None:
    """Print an active step indicator."""
    console.print(f"[bold cyan]{DIAMOND_FILL}[/]  [bold]{label}[/]")


def step_done(label: str, value: str = "") -> None:
    """Print a completed step indicator."""
    if value:
        console.print(f"[bold cyan]{DIAMOND_OPEN}[/]  {label}: [cyan]{value}[/]")
    else:
        console.print(f"[bold cyan]{DIAMOND_OPEN}[/]  {label}")


def step_end(text: str) -> None:
    """Print the closing bar."""
    console.print(f"[bold cyan]{BOT}[/]  {text}")


def file_result(action: str, path: str) -> None:
    """Print a file creation/skip result."""
    if action == "created":
        console.print(f"[bold cyan]{BAR}[/]  [green]{CHECK} created[/]  {path}")
    else:
        console.print(f"[bold cyan]{BAR}[/]  [dim]{SKIP} skipped[/]  {path}")


def summary_box(title: str, rows: list[tuple[str, str]]) -> None:
    """Print a bordered summary box connected to the bar."""
    key_width = max(len(k) for k, _ in rows) if rows else 10
    content_width = max(len(v) for _, v in rows) if rows else 10
    inner_width = key_width + 3 + content_width + 2
    min_width = max(inner_width, len(title) + 4)

    header_dashes = DASH * (min_width - len(title) - 1)
    console.print(f"[bold cyan]{BAR}[/]")
    console.print(f"[bold cyan]{TEE}{DASH}{DASH}[/] {title} [bold cyan]{header_dashes}{CORNER_TR}[/]")
    console.print(f"[bold cyan]{BAR}[/]{' ' * (min_width + 3)}[bold cyan]{BAR}[/]")
    for key, val in rows:
        padded_key = key.ljust(key_width)
        line = f"  {padded_key}   {val}"
        padding = min_width + 3 - len(line)
        console.print(f"[bold cyan]{BAR}[/]{line}{' ' * max(padding, 0)}[bold cyan]{BAR}[/]")
    console.print(f"[bold cyan]{BAR}[/]{' ' * (min_width + 3)}[bold cyan]{BAR}[/]")
    console.print(f"[bold cyan]{TEE}{DASH * (min_width + 3)}{CORNER_BR}[/]")
    console.print(f"[bold cyan]{BAR}[/]")


def next_steps(items: list[str]) -> None:
    """Print numbered next-steps list."""
    step_done("Next steps")
    for i, item in enumerate(items, 1):
        bar(f"{i}. {item}")
    bar()


# ── Interactive wrappers (non-TTY safe) ─────────────────────────────


def select(message: str, choices: list[str], default: str | None = None) -> str:
    """Arrow-key selection prompt; returns default on non-TTY."""
    if not _is_interactive():
        return default or choices[0]
    return questionary.select(message, choices=choices, default=default, style=QS).ask() or (
        default or choices[0]
    )


def confirm(message: str, default: bool = True) -> bool:
    """Yes/No confirm; returns default on non-TTY."""
    if not _is_interactive():
        return default
    result = questionary.confirm(message, default=default, style=QS).ask()
    return result if result is not None else default


def text_input(message: str, default: str = "") -> str:
    """Text input; returns default on non-TTY."""
    if not _is_interactive():
        return default
    return questionary.text(message, default=default, style=QS).ask() or default
