"""Rich terminal rendering for progress, maps, and Winnability Reports."""

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text
from ariadne.core.models import PrunedSubgrid, RunSummary

console = Console()


def render_header(project_name: str, command: str, licensee: str) -> None:
    console.print(
        Panel.fit(
            f"[bold magenta]ARIADNE[/bold magenta] - Procedural World Verifier\n"
            f"[dim]Project :[/dim] [bold]{project_name}[/bold]\n"
            f"[dim]Target  :[/dim] {command}\n"
            f"[dim]License :[/dim] [cyan]{licensee}[/cyan]",
            border_style="magenta",
        )
    )


def render_minimal_failing_map(pruned: PrunedSubgrid, seed: int) -> None:
    """Render Minimal Failing Map with highlighted characters and original coordinates."""
    fix_set = set(pruned.fix_candidates)

    # Build styled ASCII grid
    styled_rows = []
    for y, row in enumerate(pruned.subgrid.cells):
        t = Text()
        for x, ch in enumerate(row):
            if (x, y) in fix_set:
                t.append("!", style="bold yellow on red")
            elif ch == "#":
                t.append(ch, style="dim white")
            elif ch == ".":
                t.append(ch, style="cyan")
            elif ch == "@":
                t.append(ch, style="bold cyan")
            elif ch == ">":
                t.append(ch, style="bold red")
            elif ch.startswith("k") or ch == "k":
                t.append(ch, style="bold yellow")
            elif ch.startswith("D") or ch == "D":
                t.append(ch, style="bold red")
            else:
                t.append(ch, style="white")
        styled_rows.append(t)

    map_display = Text("\n").join(styled_rows)

    hint_line = ""
    if pruned.fix_hint:
        hint_line = f"\n- Chokepoint Hint : [bold yellow]{escape(pruned.fix_hint)}[/bold yellow]"

    info_panel = (
        f"[bold red]SEED FAILURE DETECTED[/bold red]\n"
        f"- Seed ID        : [bold]{seed}[/bold]\n"
        f"- Rule Violated  : [bold red]{pruned.rule_violated}[/bold red]\n"
        f"- Explanation    : {escape(pruned.failure_description)}\n"
        f"- Crop Region    : [cyan]{escape(pruned.label)}[/cyan]\n"
        f"- Coordinates    : 0-indexed, (x=col, y=row), (0,0) at top-left\n"
        f"- Sliced Edges   : Outside boundary verified as solid wall"
        f"{hint_line}"
    )

    crop_title = escape(
        f"Minimal Failing Map ({pruned.subgrid.width}x{pruned.subgrid.height}) "
        f"[x:{pruned.x_min}..{pruned.x_max}, y:{pruned.y_min}..{pruned.y_max}]"
    )
    console.print(Panel(info_panel, border_style="red", title="Counterexample Details"))
    console.print(
        Panel.fit(
            map_display,
            border_style="red",
            title=crop_title,
        )
    )
    if fix_set:
        console.print(
            "  [dim]Legend: [bold cyan]@[/bold cyan] Start, "
            "[bold red]>[/bold red] Exit, "
            "[bold yellow on red]![/bold yellow on red] Chokepoint Wall (turning into floor restores path)[/dim]\n"
        )


def render_summary(summary: RunSummary) -> None:
    """Render the final Winnability Report card."""
    ratio = summary.solvability_ratio * 100.0
    status_style = "bold green" if summary.failed_seeds == 0 else "bold red"
    status_text = "[OK] ALL SEEDS SOLVABLE" if summary.failed_seeds == 0 else "[FAIL] SOFTLOCKS/FAILURES DETECTED"

    rate_speed = int(summary.total_seeds / summary.duration_seconds) if summary.duration_seconds > 0 else 0

    content = (
        f"[{status_style}]{status_text}[/{status_style}]\n\n"
        f"- Total Evaluated : [bold]{summary.total_seeds:,}[/bold] seeds\n"
        f"- Solvability     : [{status_style}]{ratio:.2f}%[/{status_style}] "
        f"({summary.passed_seeds:,} passed / {summary.failed_seeds:,} failed)\n"
        f"- Failure Types   : {summary.property_violations} Violations, "
        f"{summary.timeouts} Timeouts, {summary.crashes} Crashes\n"
        f"- Vault Replay    : {summary.vault_replayed} replayed, {summary.vault_regressions} regressions\n"
        f"- Execution Time  : {summary.duration_seconds:.2f}s ({rate_speed:,} seeds/s)"
    )

    console.print(
        Panel(
            content,
            border_style="green" if summary.failed_seeds == 0 else "red",
            title="Ariadne Winnability Report",
        )
    )
