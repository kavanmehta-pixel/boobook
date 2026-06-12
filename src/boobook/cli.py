"""Boobook CLI — maritime AIS/RF validation."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def cmd_validate_ais(args) -> int:
    from boobook.ingest.amsa_cts import normalise_file
    from boobook.analytics.ais_anomaly import write_validation_outputs
    df = normalise_file(args.input)
    paths = write_validation_outputs(df, args.out, gap_hours=args.gap_hours)
    s = json.loads(Path(paths["summary"]).read_text())
    print(f"✓ {s['rows']} rows · {s['vessels']} vessels · {s['alerts']} alerts "
          f"({s['high_alerts']} HIGH, {s['medium_alerts']} MEDIUM)")
    print(json.dumps({"outputs": paths, "summary": s}, indent=2))
    return 0

def cmd_dashboard(args) -> int:
    from boobook.dashboard.export import export_dashboard
    out = export_dashboard(args.processed, args.out)
    print(f"✓ Dashboard: {out}")
    return 0

def cmd_coverage(args) -> int:
    from boobook.rf.coverage import cluster_summary
    print(json.dumps(cluster_summary(), indent=2))
    return 0

def cmd_rf_demo(args) -> int:
    from boobook.rf.simulate import run_rf_simulation
    r = run_rf_simulation(args.out)
    print(f"✓ TDOA fix error: {r['position_error_m']:.0f} m (simulation only)")
    print(json.dumps(r, indent=2))
    return 0

def cmd_demo(args) -> int:
    from boobook.ingest.amsa_cts import normalise_file
    from boobook.analytics.ais_anomaly import write_validation_outputs
    from boobook.dashboard.export import export_dashboard
    from boobook.rf.simulate import run_rf_simulation
    sample = Path(__file__).parent.parent.parent.parent / "data/sample/sample_ais_events.csv"
    if not sample.exists():
        sample = Path("data/sample/sample_ais_events.csv")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = normalise_file(sample)
    paths = write_validation_outputs(df, out_dir)
    dash = export_dashboard(out_dir, out_dir / "Boobook_Investor_Dashboard.html")
    rf = run_rf_simulation(out_dir)
    s = json.loads(Path(paths["summary"]).read_text())
    print(f"✓ Demo complete → {out_dir}")
    print(f"  AIS: {s['rows']} rows, {s['vessels']} vessels, {s['alerts']} alerts")
    print(f"  RF:  TDOA sim error {rf['position_error_m']:.0f} m (simulation, not field-tested)")
    print(f"  Dashboard: {dash}")
    return 0

def build_parser():
    p = argparse.ArgumentParser(prog="boobook", description="Boobook maritime AIS/RF validation")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("validate-ais", help="Normalise AIS CSV and generate anomaly alerts")
    s.add_argument("input", help="Raw AMSA/CTS-style CSV or ZIP")
    s.add_argument("--out", default="data/processed/sample")
    s.add_argument("--gap-hours", type=float, default=2.0)
    s.set_defaults(func=cmd_validate_ais)

    s = sub.add_parser("dashboard", help="Build HTML dashboard from processed outputs")
    s.add_argument("--processed", default="data/processed/sample")
    s.add_argument("--out", default="artifacts/Boobook_Investor_Dashboard.html")
    s.set_defaults(func=cmd_dashboard)

    s = sub.add_parser("coverage", help="RF cluster coverage summary")
    s.set_defaults(func=cmd_coverage)

    s = sub.add_parser("rf-demo", help="Run TDOA simulation")
    s.add_argument("--out", default="artifacts")
    s.set_defaults(func=cmd_rf_demo)

    s = sub.add_parser("demo", help="Full end-to-end demo: AIS + dashboard + RF")
    s.add_argument("--out", default="artifacts/demo")
    s.set_defaults(func=cmd_demo)

    return p

def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
