"""Demo helpers for the ACBench local prototype."""

from __future__ import annotations

from pathlib import Path

from acbench.evaluate import evaluate_predictions
from acbench.report import write_markdown_report


def run_local_demo(output_dir: str | Path) -> dict:
    """Run the local gold suite and produce JSON and markdown outputs."""

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "local_suite_eval.json"
    md_path = target_dir / "local_suite_report.md"

    results = evaluate_predictions(
        manifest_path=Path("acbench/manifests/local_suite.json"),
        predictions_path=Path("acbench/predictions/local_gold.json"),
        output_path=json_path,
    )
    write_markdown_report(results, md_path)
    return {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "results": results,
    }
