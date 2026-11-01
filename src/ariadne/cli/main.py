"""Ariadne root Typer CLI."""

import importlib.resources
from pathlib import Path
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from ariadne.core.config import load_config
from ariadne.core.errors import AriadneError, ConfigError
from ariadne.license.verifier import get_active_license
from ariadne.runner.engine import LabyrinthosRunner
from ariadne.ui.renderer import (
    render_header,
    render_minimal_failing_map,
    render_summary,
)
from ariadne.vault.manager import VaultManager

app = typer.Typer(
    name="ariadne",
    help="Ariadne: Automated verification & Minimal Failing Map pruner for procedural game worlds.",
    no_args_is_help=True,
)
vault_app = typer.Typer(name="vault", help="Inspect and manage Seed Vault regressions.")
app.add_typer(vault_app)

console = Console()


@app.command()
def init(
    template: str = typer.Option("godot4", "--template", "-t", help="Template to scaffold: godot4 or python"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing configuration"),
):
    """Scaffold ariadne.toml configuration and starter adapter template."""
    toml_path = Path("ariadne.toml")
    if toml_path.exists() and not force:
        console.print("[yellow]ariadne.toml already exists. Use --force to overwrite.[/yellow]")
        raise typer.Exit(code=2)

    templates_pkg = importlib.resources.files("ariadne.cli") / "templates"

    if template.lower() == "python":
        adapter_file = "sample_generator.py"
        adapter_dest = Path("ariadne_adapter.py")
        command_str = "python ariadne_adapter.py"
    else:
        adapter_file = "sample_generator.gd"
        adapter_dest = Path("ariadne_adapter.gd")
        command_str = "godot_console.exe --headless -s ariadne_adapter.gd"

    # Copy adapter via importlib.resources (portable across source, wheel, and PyInstaller)
    adapter_bytes = (templates_pkg / adapter_file).read_bytes()
    adapter_dest.write_bytes(adapter_bytes)
    console.print(f"[green][OK][/green] Created starter adapter: [bold]{adapter_dest}[/bold]")

    # Create ariadne.toml
    toml_content = f"""schema_version = 1

[project]
name = "MyRoguelike"
command = "{command_str}"
startup_timeout_ms = 5000
seed_timeout_ms = 500

[seeds]
base_seed = 1337
count = 1000

[legend]
"#" = "wall"
"." = "floor"
"@" = "start"
">" = "exit"

[rules]
reachable = {{ from = "@", to = ">" }}
connected_walkable = true
key_before_door = false
"""
    with open(toml_path, "w", encoding="utf-8") as f:
        f.write(toml_content)
    console.print(f"[green][OK][/green] Created configuration: [bold]{toml_path}[/bold]")

    # Ensure .gitignore has license.key
    gitignore_path = Path(".gitignore")
    ignore_entry = ".ariadne/license.key\n"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if ".ariadne/license.key" not in content:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# Ariadne offline license\n" + ignore_entry)
            console.print("[green][OK][/green] Appended .ariadne/license.key to .gitignore")
    else:
        gitignore_path.write_text("# Ariadne offline license\n" + ignore_entry, encoding="utf-8")
        console.print("[green][OK][/green] Created .gitignore with .ariadne/license.key")

    console.print(
        "\n[bold green]Ariadne initialized successfully![/bold green]\n"
        "Run your first test with sample buggy generator:\n"
        "  [cyan]ariadne run --seeds 100[/cyan]\n"
    )


@app.command()
def run(
    config_file: str = typer.Option("ariadne.toml", "--config", "-c", help="Path to configuration file"),
    seeds: Optional[int] = typer.Option(None, "--seeds", "-s", help="Number of seeds to evaluate"),
    base_seed: Optional[int] = typer.Option(None, "--base-seed", "-b", help="Base starting seed integer"),
    vault_only: bool = typer.Option(False, "--vault-only", help="Only replay seeds recorded in Seed Vault"),
    no_vault: bool = typer.Option(False, "--no-vault", help="Skip replaying Seed Vault"),
    timeout_ms: Optional[int] = typer.Option(None, "--timeout-ms", help="Override per-seed timeout in milliseconds"),
):
    """Run mass-seed evaluation and verify topological invariants."""
    try:
        config = load_config(config_file)
    except ConfigError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        raise typer.Exit(code=2)

    # Check license
    license_info = get_active_license()

    total_seeds = seeds if seeds is not None else config.seeds.count
    if not license_info.can_run_unlimited and total_seeds > (license_info.seed_limit or 1000):
        console.print(
            f"[yellow]Community Free Tier limit is {license_info.seed_limit:,} seeds. "
            f"Clamping {total_seeds:,} -> {license_info.seed_limit:,} seeds.\n"
            f"Set ARIADNE_LICENSE_KEY to unlock unlimited seeds.[/yellow]"
        )
        total_seeds = license_info.seed_limit or 1000

    if timeout_ms is not None:
        config.project.seed_timeout_ms = timeout_ms

    render_header(config.project.name, config.project.command, license_info.licensee)

    runner = LabyrinthosRunner(config)

    start_seed = base_seed if base_seed is not None else config.seeds.base_seed
    seed_list = [] if vault_only else list(range(start_seed, start_seed + total_seeds))

    try:
        with console.status("[bold cyan]Evaluating procedural seeds...[/bold cyan]") as status:
            summary = runner.run_suite(
                seeds=seed_list,
                replay_vault=not no_vault,
                on_progress=lambda cur, tot, r: status.update(
                    f"[bold cyan]Evaluating seed {r.seed} ({cur:,}/{tot:,})...[/bold cyan]"
                ),
            )
    except AriadneError as e:
        console.print(f"[bold red]Execution Aborted:[/bold red] {e}")
        runner.close()
        raise typer.Exit(code=2)
    except KeyboardInterrupt:
        console.print("\n[yellow]Run cancelled by user.[/yellow]")
        runner.close()
        raise typer.Exit(code=2)

    runner.close()

    # Render Counterexamples
    if summary.failures:
        console.print("\n")
        # Display the smallest Minimal Failing Map
        failing_with_maps = [f for f in summary.failures if f.pruned_map is not None]
        if failing_with_maps:
            # Sort by area (smallest first)
            failing_with_maps.sort(key=lambda f: f.pruned_map.subgrid.width * f.pruned_map.subgrid.height)
            smallest = failing_with_maps[0]
            render_minimal_failing_map(smallest.pruned_map, smallest.seed)
        else:
            first_fail = summary.failures[0]
            console.print(
                f"[bold red]Failure on Seed {first_fail.seed}:[/bold red] {first_fail.error_message}"
            )

    console.print("\n")
    render_summary(summary)

    if summary.failed_seeds > 0:
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)


@vault_app.command("list")
def vault_list(
    vault_file: str = typer.Option(".ariadne/vault.jsonl", "--vault", help="Path to vault file")
):
    """List all regression seeds recorded in the Seed Vault."""
    manager = VaultManager(vault_file)
    entries = manager.load_entries()

    if not entries:
        console.print("[green]Seed Vault is clean. No failing seeds recorded.[/green]")
        raise typer.Exit(code=0)

    table = Table(title=f"Ariadne Seed Vault ({len(entries)} regressions)")
    table.add_column("Seed", justify="right", style="cyan")
    table.add_column("Error Type", style="bold red")
    table.add_column("Rule", style="yellow")
    table.add_column("Grid Hash", style="dim")
    table.add_column("Recorded At", style="white")

    for entry in entries:
        h = entry.get("grid_hash")
        h_str = h[:12] + "..." if h else "—"
        table.add_row(
            str(entry.get("seed", 0)),
            entry.get("error_type", "unknown"),
            entry.get("rule") or "—",
            h_str,
            entry.get("created_at", "—")[:19],
        )

    console.print(table)


@vault_app.command("clear")
def vault_clear(
    vault_file: str = typer.Option(".ariadne/vault.jsonl", "--vault", help="Path to vault file"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Clear all records in the Seed Vault."""
    manager = VaultManager(vault_file)
    if not yes:
        confirm = typer.confirm("Are you sure you want to delete all recorded regression seeds?")
        if not confirm:
            raise typer.Exit(code=0)

    manager.clear()
    console.print("[green]Seed Vault cleared successfully.[/green]")


def main():
    app()


if __name__ == "__main__":
    main()
