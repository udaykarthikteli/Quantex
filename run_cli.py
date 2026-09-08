"""
Quantex CLI Benchmark & Runner.
Enables running batch simulations, comparisons, and route generation from command-line.
"""

import argparse
import sys
import json
import io

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from quantex.data.presets import PRESETS
from quantex.core.qubo_formulator import QUBOFormulator
from quantex.hybrid.cluster_router import HybridClusterRouter
from quantex.classical.classical_solvers import ClassicalSolvers
from quantex.quantum.qaoa_solver import QAOASolver
from quantex.quantum.vqe_solver import VQESolver
from quantex.quantum.quantum_inspired import QuantumInspiredSolver


def main():
    parser = argparse.ArgumentParser(
        description="Quantex: Quantum Fleet & Last-Mile Logistics Optimization Engine"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="E-Commerce Last-Mile Express",
        choices=list(PRESETS.keys()),
        help="Select logistics scenario preset"
    )
    parser.add_argument(
        "--solver",
        type=str,
        default="qaoa",
        choices=["qaoa", "vqe", "qisa", "classical", "all"],
        help="Quantum / Classical solver engine"
    )
    parser.add_argument(
        "--reps",
        type=int,
        default=1,
        help="QAOA/VQE circuit repetition depth"
    )
    parser.add_argument(
        "--export-json",
        type=str,
        default=None,
        help="Optional path to export JSON results"
    )

    args = parser.parse_args()
    console = Console(file=sys.stdout)

    console.print(Panel.fit(
        f"[bold cyan]⚡ QUANTEX: Quantum Fleet Routing Engine[/bold cyan]\n"
        f"[green]Scenario:[/green] {args.scenario} | [yellow]Solver:[/yellow] {args.solver.upper()}",
        border_style="cyan"
    ))

    problem = PRESETS[args.scenario]()
    console.print(f"📦 Loaded [bold]{len(problem.nodes)}[/bold] delivery stops across [bold]{len(problem.vehicles)}[/bold] fleet vehicles.\n")

    if args.solver in ["qaoa", "vqe", "qisa"]:
        router = HybridClusterRouter(quantum_backend=args.solver, qaoa_reps=args.reps)
        console.print(f"[bold green]Running Quantum Optimization ({args.solver.upper()})...[/bold green]")
        results = router.solve_cvrp(problem)

        table = Table(title="🚀 Fleet Dispatch & Environmental Sustainability Summary")
        table.add_column("Vehicle", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Route Plan", style="yellow")
        table.add_column("Dist (km)", justify="right")
        table.add_column("Time (min)", justify="right")
        table.add_column("Fuel", justify="right")
        table.add_column("CO2 (kg)", justify="right", style="green")
        table.add_column("Cost ($)", justify="right")

        for v in results["fleet_sustainability"]:
            route_str = " ➔ ".join(f"Node {n}" for n in v["route"])
            table.add_row(
                v["vehicle_name"],
                v["vehicle_type"],
                route_str,
                f"{v['distance_km']:.2f}",
                f"{v['total_time_min']:.1f}",
                f"{v['fuel_consumed']:.2f} {v['fuel_unit']}",
                f"{v['co2_emissions_kg']:.2f}",
                f"${v['total_operational_cost']:.2f}"
            )

        console.print(table)

        # Baseline Comparison
        comp = results["baseline_comparison"]
        console.print("\n[bold green]🌱 Green Logistics & Optimization Impact vs Baseline:[/bold green]")
        console.print(f" • Distance Saved: [bold]{comp['distance_saved_km']} km[/bold] ({comp['distance_pct_saved']}%)")
        console.print(f" • Carbon Abated: [bold]{comp['co2_saved_kg']} kg CO2[/bold] ({comp['co2_pct_saved']}%)")
        console.print(f" • Fuel Saved: [bold]{comp['fuel_saved']} L/kWh[/bold] ({comp['fuel_pct_saved']}%)")
        console.print(f" • Time Saved: [bold]{comp['time_saved_min']} mins[/bold] ({comp['time_pct_saved']}%)")
        console.print(f" • Financial Savings: [bold]${comp['cost_saved_usd']}[/bold] ({comp['cost_pct_saved']}%)\n")

        if args.export_json:
            with open(args.export_json, "w") as f:
                json.dump(results["aggregated_metrics"], f, indent=2)
            console.print(f"💾 Results exported to {args.export_json}")

    elif args.solver == "all":
        console.print("[bold yellow]Running Head-to-Head Solver Arena...[/bold yellow]")
        solvers = ["classical", "qaoa", "vqe", "qisa"]
        arena_table = Table(title="⚡ Quantum vs Classical Solver Benchmark")
        arena_table.add_column("Solver", style="cyan")
        arena_table.add_column("Distance (km)", justify="right")
        arena_table.add_column("CO2 (kg)", justify="right", style="green")
        arena_table.add_column("Cost ($)", justify="right")

        for s in solvers:
            if s == "classical":
                router = HybridClusterRouter(quantum_backend="qisa")
                res = router.solve_cvrp(problem)
                m = res["baseline_comparison"]
                dist = res["aggregated_metrics"]["distance_km"] + m["distance_saved_km"]
                co2 = res["aggregated_metrics"]["co2_emissions_kg"] + m["co2_saved_kg"]
                cost = res["aggregated_metrics"]["total_operational_cost"] + m["cost_saved_usd"]
                arena_table.add_row("Classical Baseline (Greedy)", f"{dist:.2f}", f"{co2:.2f}", f"${cost:.2f}")
            else:
                router = HybridClusterRouter(quantum_backend=s, qaoa_reps=args.reps)
                res = router.solve_cvrp(problem)
                m = res["aggregated_metrics"]
                arena_table.add_row(f"Quantum ({s.upper()})", f"{m['distance_km']:.2f}", f"{m['co2_emissions_kg']:.2f}", f"${m['total_operational_cost']:.2f}")

        console.print(arena_table)


if __name__ == "__main__":
    main()
