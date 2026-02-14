#!/usr/bin/env python3
"""Local-only visual regression workflow for template/planner refactors."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from planner.main import generate_planner
from planner.templates import generate_template

DEVICES = ("remarkable", "scribe", "palma")
PLANNER_CANARY_DEVICES = ("remarkable",)
TEMPLATE_CANARY_CASES = (
    ("lines", {}, "lines"),
    ("grid", {}, "grid"),
    ("day-at-glance", {}, "day_at_glance"),
    ("schedule", {}, "schedule"),
    ("notes", {"param_overrides": {"notes_fill": "millimeter"}}, "notes_millimeter"),
)
YEAR = 2026
DPI = 200
DEFAULT_RMSE_THRESHOLD = 0.002
DEFAULT_CHANGED_PIXEL_RATIO = 0.005

REGRESSION_ROOT = Path("generated/regression")
NULL_OUTPUT = "null:"


@dataclass(frozen=True)
class DiffResult:
    """One per-image diff result."""

    path: str
    rmse_normalized: float
    changed_pixel_ratio: float
    passed: bool
    reason: str = ""


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, capture_output=True, text=True)


def _ensure_tool(name: str) -> None:
    if shutil.which(name) is None:
        msg = f"required tool '{name}' is not available in PATH."
        raise RuntimeError(msg)


def _prepare_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def _pdf_root(kind: str) -> Path:
    return REGRESSION_ROOT / kind / "pdf"


def _png_root(kind: str) -> Path:
    return REGRESSION_ROOT / kind / "png"


def _diff_root() -> Path:
    return REGRESSION_ROOT / "diff"


def _generate_outputs(
    kind: str,
    *,
    include_planner: bool,
    planner_devices: tuple[str, ...],
) -> None:
    pdf_root = _pdf_root(kind)
    _prepare_dir(pdf_root)

    generated_pdf_count = 0
    for device in DEVICES:
        device_root = pdf_root / device
        templates_root = device_root / "templates"
        templates_root.mkdir(parents=True, exist_ok=True)

        if include_planner and device in planner_devices:
            generate_planner(
                year=YEAR,
                output_path=device_root / f"planner_{YEAR}.pdf",
                device=device,
            )
            generated_pdf_count += 1

        for template, params, output_stem in TEMPLATE_CANARY_CASES:
            generate_template(
                template=template,
                device=device,
                output_path=templates_root / f"{output_stem}.pdf",
                param_overrides=params.get("param_overrides"),
            )
            generated_pdf_count += 1

    print(f"Generated {generated_pdf_count} PDF file(s) for '{kind}'.")


def _rasterize_outputs(
    kind: str,
    *,
    dpi: int,
    planner_pages: int,
) -> None:
    _ensure_tool("pdftoppm")
    pdf_root = _pdf_root(kind)
    png_root = _png_root(kind)
    _prepare_dir(png_root)

    rasterized_pdf_count = 0
    for pdf_path in sorted(pdf_root.rglob("*.pdf")):
        relative_stem = pdf_path.relative_to(pdf_root).with_suffix("")
        png_prefix = png_root / relative_stem
        png_prefix.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "pdftoppm",
            "-png",
            "-r",
            str(dpi),
        ]
        if pdf_path.name.startswith("planner_") and planner_pages > 0:
            command.extend(["-f", "1", "-l", str(planner_pages)])
        command.extend([str(pdf_path), str(png_prefix)])
        _run(command)
        rasterized_pdf_count += 1

    print(f"Rasterized {rasterized_pdf_count} PDF file(s) for '{kind}'.")


def _image_dimensions(image_path: Path) -> tuple[int, int]:
    _ensure_tool("magick")
    output = _run(
        [
            "magick",
            "identify",
            "-format",
            "%w %h",
            str(image_path),
        ]
    ).stdout.strip()
    width_text, height_text = output.split()
    return int(width_text), int(height_text)


def _compare_metric(
    *,
    metric: str,
    baseline: Path,
    candidate: Path,
    output_path: Path | None = None,
) -> str:
    command = [
        "magick",
        "compare",
        "-metric",
        metric,
        str(baseline),
        str(candidate),
        str(output_path) if output_path is not None else NULL_OUTPUT,
    ]
    result = _run(command, check=False)
    metric_output = result.stderr.strip() or result.stdout.strip()
    return metric_output


def _parse_normalized_rmse(metric_output: str) -> float:
    # ImageMagick RMSE metric format is typically: "<abs> (<normalized>)".
    match = re.search(r"\(([^)]+)\)", metric_output)
    if match:
        return float(match.group(1))
    return float(metric_output.split()[0])


def _parse_changed_pixels(metric_output: str) -> int:
    return int(float(metric_output.split()[0]))


def _diff_outputs(
    *,
    rmse_threshold: float,
    changed_pixel_ratio_threshold: float,
) -> int:
    _ensure_tool("magick")
    baseline_root = _png_root("baseline")
    candidate_root = _png_root("candidate")
    diff_root = _diff_root()
    images_root = diff_root / "images"
    _prepare_dir(images_root)

    if not baseline_root.exists():
        raise RuntimeError("baseline PNG set does not exist. Run the baseline command first.")
    if not candidate_root.exists():
        raise RuntimeError("candidate PNG set does not exist. Run the candidate command first.")

    results: list[DiffResult] = []
    failures = 0

    baseline_images = sorted(baseline_root.rglob("*.png"))
    baseline_relatives = {path.relative_to(baseline_root) for path in baseline_images}
    candidate_relatives = {path.relative_to(candidate_root) for path in candidate_root.rglob("*.png")}

    for relative in sorted(baseline_relatives | candidate_relatives):
        baseline_image = baseline_root / relative
        candidate_image = candidate_root / relative

        if not baseline_image.exists():
            failures += 1
            results.append(
                DiffResult(
                    path=str(relative),
                    rmse_normalized=1.0,
                    changed_pixel_ratio=1.0,
                    passed=False,
                    reason="candidate image has no baseline match",
                )
            )
            continue
        if not candidate_image.exists():
            failures += 1
            results.append(
                DiffResult(
                    path=str(relative),
                    rmse_normalized=1.0,
                    changed_pixel_ratio=1.0,
                    passed=False,
                    reason="baseline image missing in candidate output",
                )
            )
            continue

        diff_image = images_root / relative
        diff_image.parent.mkdir(parents=True, exist_ok=True)

        rmse_metric = _compare_metric(
            metric="RMSE",
            baseline=baseline_image,
            candidate=candidate_image,
            output_path=None,
        )
        ae_metric = _compare_metric(
            metric="AE",
            baseline=baseline_image,
            candidate=candidate_image,
            output_path=diff_image,
        )
        rmse_normalized = _parse_normalized_rmse(rmse_metric)
        changed_pixels = _parse_changed_pixels(ae_metric)
        width, height = _image_dimensions(baseline_image)
        changed_ratio = changed_pixels / (width * height)
        passed = (rmse_normalized <= rmse_threshold) and (changed_ratio <= changed_pixel_ratio_threshold)
        if not passed:
            failures += 1
        elif diff_image.exists():
            diff_image.unlink()

        results.append(
            DiffResult(
                path=str(relative),
                rmse_normalized=rmse_normalized,
                changed_pixel_ratio=changed_ratio,
                passed=passed,
            )
        )

    summary = {
        "failures": failures,
        "total": len(results),
        "rmse_threshold": rmse_threshold,
        "changed_pixel_ratio_threshold": changed_pixel_ratio_threshold,
        "results": [asdict(result) for result in results],
    }
    diff_root.mkdir(parents=True, exist_ok=True)
    (diff_root / "report.json").write_text(json.dumps(summary, indent=2))

    print(f"Compared {len(results)} image(s).")
    print(f"Failures: {failures}")
    print(f"Thresholds: rmse<={rmse_threshold}, changed_pixel_ratio<={changed_pixel_ratio_threshold}")
    print(f"Report: {diff_root / 'report.json'}")
    if failures:
        print(f"Diff images: {images_root}")

    return 1 if failures else 0


def _clean_outputs() -> None:
    shutil.rmtree(REGRESSION_ROOT, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local visual regression helper.")
    parser.add_argument(
        "--dpi",
        type=int,
        default=DPI,
        help="Rasterization DPI for pdftoppm.",
    )
    parser.add_argument(
        "--include-planner",
        action="store_true",
        help="Also generate planner PDFs for canary comparison.",
    )
    parser.add_argument(
        "--planner-pages",
        type=int,
        default=4,
        help="Planner page count to rasterize from page 1 when planner comparison is enabled.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("baseline", help="Generate and rasterize baseline outputs.")
    subparsers.add_parser("candidate", help="Generate and rasterize candidate outputs.")

    diff_parser = subparsers.add_parser("diff", help="Compare baseline and candidate PNG outputs.")
    diff_parser.add_argument(
        "--rmse-threshold",
        type=float,
        default=DEFAULT_RMSE_THRESHOLD,
        help="Maximum normalized RMSE accepted per image.",
    )
    diff_parser.add_argument(
        "--pixel-threshold",
        type=float,
        default=DEFAULT_CHANGED_PIXEL_RATIO,
        help="Maximum changed pixel ratio accepted per image.",
    )

    subparsers.add_parser("clean", help="Delete local regression outputs.")
    args = parser.parse_args()

    if args.command == "baseline":
        _generate_outputs(
            "baseline",
            include_planner=args.include_planner,
            planner_devices=PLANNER_CANARY_DEVICES,
        )
        _rasterize_outputs("baseline", dpi=args.dpi, planner_pages=args.planner_pages)
        return 0

    if args.command == "candidate":
        _generate_outputs(
            "candidate",
            include_planner=args.include_planner,
            planner_devices=PLANNER_CANARY_DEVICES,
        )
        _rasterize_outputs("candidate", dpi=args.dpi, planner_pages=args.planner_pages)
        return 0

    if args.command == "diff":
        return _diff_outputs(
            rmse_threshold=args.rmse_threshold,
            changed_pixel_ratio_threshold=args.pixel_threshold,
        )

    if args.command == "clean":
        _clean_outputs()
        return 0

    parser.exit(status=2, message=f"error: unknown command '{args.command}'\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
