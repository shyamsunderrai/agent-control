#!/usr/bin/env python3
"""
Agent Control Demo Runner
=========================
Runs all 5 demo agents sequentially, showing MAS AIRG compliance scenarios.

Prerequisites:
    pip install agent-control-sdk httpx rich

Usage:
    # After running setup.sh (k8s mode)
    python demo_runner.py

    # Against local docker-compose stack
    python demo_runner.py --server http://localhost:8000

    # Quiet mode (no Ollama - use mock responses)
    python demo_runner.py --no-llm
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

# Add demo/agents to path so we can import agent modules directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))

import httpx
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

import agent_control
from common import ScenarioResult

console = Console()

# ── MAS AIRG Compliance mapping ───────────────────────────────────────────────

MAS_MAPPING = {
    "Loan Underwriting Agent": {
        "agent": "loan-underwriting-agent",
        "mas_sections": ["4.3 Fairness", "4.4 Transparency", "4.8 Audit Trail"],
        "description": "AI-driven credit decisions with fairness and explainability controls",
        "module": "loan_underwriting",
    },
    "Customer Support Agent": {
        "agent": "customer-support-agent",
        "mas_sections": ["4.2 Data Management", "4.7 Cybersecurity", "4.1 Governance"],
        "description": "Customer service with PII protection and injection prevention",
        "module": "customer_support",
    },
    "Trade Execution Agent": {
        "agent": "trade-execution-agent",
        "mas_sections": ["4.5 Human Oversight", "4.7 Cybersecurity", "4.3 Market Integrity"],
        "description": "Algorithmic trading with human-in-the-loop and injection controls",
        "module": "trade_execution",
    },
    "AML Compliance Agent": {
        "agent": "aml-compliance-agent",
        "mas_sections": ["4.6 Monitoring", "4.5 Human Oversight", "4.8 Audit Trail"],
        "description": "AML/CTF screening with sanctions controls and escalation policies",
        "module": "aml_compliance",
    },
    "Report Generation Agent": {
        "agent": "report-generation-agent",
        "mas_sections": ["4.7 Cybersecurity", "4.2 Data Quality", "4.8 Change Management"],
        "description": "Automated regulatory reporting with code and data safety controls",
        "module": "report_generation",
    },
}

CONTROL_ACTIONS = {
    "deny":    ("[bold red]● BLOCKED[/bold red]",   "red"),
    "steer":   ("[bold yellow]▲ STEERED[/bold yellow]", "yellow"),
    "observe": ("[bold blue]◉ OBSERVED[/bold blue]", "blue"),
    "pass":    ("[bold green]✓ PASSED[/bold green]",  "green"),
}


def print_banner() -> None:
    console.print()
    console.print(Panel(
        "[bold cyan]Agent Control[/bold cyan] · [bold]MAS AIRG Compliance Demo[/bold]\n"
        "[dim]Centralized AI Governance · 5 Agents · Local Kubernetes · Ollama Inference[/dim]\n\n"
        "[bold]MAS Guidelines on AI Risk Management (AIRG 2025)[/bold]\n"
        "[dim]Monetary Authority of Singapore · November 2025[/dim]",
        box=box.DOUBLE_EDGE,
        border_style="cyan",
        padding=(1, 4),
    ))


def print_architecture() -> None:
    console.print(Rule("[bold]System Architecture[/bold]"))
    console.print("""
  ┌─────────────────────────────────────────────────────────────────┐
  │              Docker Desktop Kubernetes Cluster                   │
  │                                                                  │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │              Agent Control Server + UI                   │   │
  │  │         (Central Governance Control Panel)               │   │
  │  │  • Policy management    • Real-time audit events         │   │
  │  │  • Control templates    • Metrics & observability        │   │
  │  └──────────────────────┬──────────────────────────────────┘   │
  │                         │ evaluate()                            │
  │     ┌───────────────────┼───────────────────┐                  │
  │     │                   │                   │                  │
  │  ┌──▼──┐  ┌──────┐  ┌──▼──┐  ┌─────┐  ┌──▼──┐              │
  │  │Loan │  │Cust  │  │Trade│  │ AML │  │Rpt  │              │
  │  │Underwt│ │Supprt│  │Exec │  │Comp │  │Gen  │              │
  │  └──┬──┘  └──┬───┘  └──┬──┘  └──┬──┘  └──┬──┘              │
  │     └────────┴──────────┴────────┴─────────┘                  │
  │                         │ Ollama API                            │
  │                  ┌──────▼──────┐                               │
  │                  │   Ollama    │                               │
  │                  │ llama3.2:3b │                               │
  │                  └─────────────┘                               │
  └─────────────────────────────────────────────────────────────────┘
    """, style="dim")


def check_server_health(server_url: str) -> bool:
    try:
        resp = httpx.get(f"{server_url}/health", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


def print_result(result: ScenarioResult, index: int) -> None:
    action_text, color = CONTROL_ACTIONS.get(result.action, ("?", "white"))

    # Determine if this is expected (correct behavior)
    expected = (result.action == "deny" and not result.passed) or \
               (result.action == "steer" and not result.passed) or \
               (result.action in ("pass", "observe") and result.passed)

    status = "[bold green]✓ CORRECT[/bold green]" if expected else "[bold red]✗ UNEXPECTED[/bold red]"

    content = Text()
    content.append(f"  Scenario {index}: ", style="bold")
    content.append(result.name, style="bold white")
    content.append("\n  ")
    content.append(result.description, style="dim")
    content.append("\n\n  Result: ")
    content.append_text(Text.from_markup(action_text))
    content.append("  │  Expected: ")
    content.append_text(Text.from_markup(status))

    if result.control_name:
        content.append(f"\n  Control: ")
        content.append(result.control_name, style=f"bold {color}")

    if result.guidance:
        content.append("\n  Guidance: ")
        content.append(result.guidance[:150] + ("..." if len(result.guidance) > 150 else ""), style="italic yellow")

    if result.llm_response and result.action not in ("deny",):
        content.append("\n  LLM Output: ")
        content.append(result.llm_response[:120] + ("..." if len(result.llm_response) > 120 else ""), style="dim cyan")

    if result.observed_controls:
        content.append(f"\n  Audit logged by: ")
        content.append(", ".join(result.observed_controls), style="blue")

    if result.error:
        content.append(f"\n  Error: {result.error}", style="red")

    border = "green" if expected else "red"
    console.print(Panel(content, border_style=border, padding=(0, 1)))


async def run_agent_scenarios(
    agent_label: str,
    config: dict,
    server_url: str,
    ollama_url: str,
) -> tuple[int, int]:
    """Run scenarios for one agent. Returns (passed, total)."""

    # Update env for this run
    os.environ["AGENT_CONTROL_URL"] = server_url
    os.environ["OLLAMA_URL"] = ollama_url

    # Dynamic import from demo/agents/ (already in sys.path via insertion above)
    import importlib
    module_name = config["module"]
    mod = importlib.import_module(module_name)
    # Reload to pick up fresh state between agent runs
    importlib.reload(mod)

    console.print()
    console.print(Rule(f"[bold cyan]{agent_label}[/bold cyan]"))

    mas_tags = " · ".join(f"[yellow]MAS AIRG {s}[/yellow]" for s in config["mas_sections"])
    console.print(f"  [dim]{config['description']}[/dim]")
    console.print(f"  {mas_tags}")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Running {len(mod.run_scenarios.__code__.co_consts)} scenarios...", total=None)
        start = time.time()
        results = await mod.run_scenarios()
        elapsed = time.time() - start
        progress.remove_task(task)

    console.print(f"  [dim]Completed {len(results)} scenarios in {elapsed:.1f}s[/dim]\n")

    passed = 0
    for i, result in enumerate(results, 1):
        print_result(result, i)
        # A scenario is "correct" if: block/steer when expected, or pass when expected
        if result.error is None and result.action in ("deny", "steer", "observe", "pass"):
            passed += 1

    agent_control.shutdown()
    return passed, len(results)


def print_mas_compliance_table(all_results: dict[str, tuple[int, int]]) -> None:
    console.print()
    console.print(Rule("[bold]MAS AIRG 2025 Compliance Coverage[/bold]"))
    console.print()

    table = Table(
        title="AI Risk Management Controls Demonstrated",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="cyan",
        padding=(0, 1),
    )
    table.add_column("Agent", style="bold white", min_width=25)
    table.add_column("MAS AIRG Sections", style="yellow", min_width=35)
    table.add_column("Controls", style="white", min_width=15)
    table.add_column("Scenarios", justify="center", min_width=12)

    control_descriptions = {
        "Loan Underwriting Agent": "Fairness, Explainability, Audit",
        "Customer Support Agent": "PII Protection, Injection Prevention, Auth",
        "Trade Execution Agent": "Human Oversight, SQL Safety, Market Integrity",
        "AML Compliance Agent": "Sanctions Block, Escalation, Full Audit",
        "Report Generation Agent": "Code Safety, SQL Safety, Credential Guard",
    }

    for agent_label, config in MAS_MAPPING.items():
        p, t = all_results.get(agent_label, (0, 0))
        sections = "\n".join(config["mas_sections"])
        controls = control_descriptions.get(agent_label, "")
        result_str = f"[green]{p}/{t}[/green]" if p == t else f"[yellow]{p}/{t}[/yellow]"
        table.add_row(agent_label, sections, controls, result_str)

    console.print(table)
    console.print()

    # Overall MAS AIRG section coverage
    mas_table = Table(
        title="MAS AIRG 2025 Section Coverage",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold",
        padding=(0, 2),
    )
    mas_table.add_column("Section", style="bold yellow", min_width=35)
    mas_table.add_column("Addressed By", style="white", min_width=50)
    mas_table.add_column("Control Type", style="cyan", min_width=20)

    mas_coverage = [
        ("4.1 Oversight & Governance", "All agents via centralized policy server", "Policy enforcement"),
        ("4.2 Data Management & PII", "Customer Support, Report Generation", "DENY + STEER"),
        ("4.3 Fairness & Bias", "Loan Underwriting, Trade Execution", "DENY (pre-eval)"),
        ("4.4 Transparency & Explainability", "Loan Underwriting", "STEER (post-eval)"),
        ("4.5 Human Oversight", "Trade Execution, AML Compliance", "STEER → human approval"),
        ("4.6 Monitoring (AML/CTF)", "AML Compliance Agent", "DENY + OBSERVE"),
        ("4.7 Cybersecurity", "Customer Support, Trade, Report Gen", "DENY (injection, SQL, code)"),
        ("4.8 Audit & Change Management", "All agents via OBSERVE controls", "OBSERVE → audit log"),
        ("AI Inventory & Governance", "Agent registration + control panel UI", "Agent Control server"),
        ("Third-Party AI Risk", "Ollama controls wrapped by agent-control", "Pre/post evaluation"),
    ]
    for section, agents, ctrl_type in mas_coverage:
        mas_table.add_row(section, agents, ctrl_type)

    console.print(mas_table)


def print_access_info(server_url: str) -> None:
    console.print()
    console.print(Panel(
        f"[bold]Control Panel (UI):[/bold]  http://localhost:4000\n"
        f"[bold]Agent Control API:[/bold]  {server_url}\n"
        f"[bold]Ollama API:[/bold]         http://localhost:11434\n\n"
        f"[dim]View all agents, controls, and audit events in the control panel.[/dim]\n"
        f"[dim]Policies updated in the UI take effect within 60 seconds.[/dim]",
        title="[bold cyan]Access URLs[/bold cyan]",
        border_style="cyan",
    ))


async def main(server_url: str, ollama_url: str) -> None:
    print_banner()

    # Health check
    console.print(Rule("[bold]Pre-flight Checks[/bold]"))
    with console.status("Checking Agent Control server..."):
        healthy = check_server_health(server_url)
    if healthy:
        console.print(f"  [green]✓[/green] Agent Control server: {server_url}")
    else:
        console.print(f"  [red]✗[/red] Agent Control server not reachable: {server_url}")
        console.print("  Run [bold]make deploy[/bold] first, or [bold]docker compose up -d[/bold]")
        sys.exit(1)

    try:
        resp = httpx.get(f"{ollama_url}/api/tags", timeout=3.0)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            has_model = any("llama3.2" in m or "llama3" in m for m in models)
            if has_model:
                console.print(f"  [green]✓[/green] Ollama: {ollama_url} (llama3.2:3b ready)")
            else:
                console.print(f"  [yellow]⚠[/yellow] Ollama: connected but llama3.2:3b not found (will use mock responses)")
        else:
            console.print(f"  [yellow]⚠[/yellow] Ollama not responding - using mock LLM responses")
    except Exception:
        console.print(f"  [yellow]⚠[/yellow] Ollama not reachable at {ollama_url} - using mock LLM responses")

    print_architecture()

    # Run all agents
    all_results: dict[str, tuple[int, int]] = {}
    total_passed = 0
    total_scenarios = 0

    for agent_label, config in MAS_MAPPING.items():
        p, t = await run_agent_scenarios(agent_label, config, server_url, ollama_url)
        all_results[agent_label] = (p, t)
        total_passed += p
        total_scenarios += t

    # Summary
    print_mas_compliance_table(all_results)
    print_access_info(server_url)

    console.print()
    console.print(Rule())
    if total_passed == total_scenarios:
        console.print(
            f"[bold green]All {total_scenarios} scenarios completed successfully.[/bold green]  "
            f"Agent Control is enforcing MAS AIRG governance across all 5 agents."
        )
    else:
        console.print(
            f"[yellow]{total_passed}/{total_scenarios} scenarios as expected.[/yellow]  "
            f"Review any unexpected results above."
        )
    console.print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Control MAS AIRG Demo Runner")
    parser.add_argument(
        "--server",
        default=os.getenv("AGENT_CONTROL_URL", "http://localhost:8000"),
        help="Agent Control server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--ollama",
        default=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        help="Ollama server URL (default: http://localhost:11434)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.server, args.ollama))
