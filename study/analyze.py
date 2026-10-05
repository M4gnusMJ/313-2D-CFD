#!/usr/bin/env python3
"""Summarize time-averaged drag coefficients from OpenFOAM forceCoeffs data."""

import argparse
import csv
import io
import math
import sys
from pathlib import Path


WINDOW_START = 0.5
WINDOW_MIDDLE = 0.75
WINDOW_END = 1.0


def coefficient_file(case_path):
    path = Path(case_path)
    if path.is_file():
        return path
    matches = sorted(path.rglob("coefficient.dat"))
    if len(matches) != 1:
        raise ValueError(f"{path}: expected one coefficient.dat, found {len(matches)}")
    return matches[0]


def read_coefficients(path, columns):
    indices = None
    samples = []
    with path.open() as data:
        for line in data:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                header = line[1:].split()
                if "Time" in header and all(column in header for column in columns):
                    indices = [header.index("Time")] + [header.index(column) for column in columns]
                continue
            if indices is None:
                continue
            fields = line.split()
            try:
                samples.append(tuple(float(fields[index]) for index in indices))
            except (IndexError, ValueError) as error:
                raise ValueError(f"{path}: invalid coefficient row: {line}") from error
    if len(samples) < 2:
        raise ValueError(f"{path}: expected at least two samples with columns Time and {' '.join(columns)}")
    samples.sort()
    if any(not all(math.isfinite(value) for value in sample) for sample in samples):
        raise ValueError(f"{path}: non-finite time or coefficient value")
    if any(samples[i][0] >= samples[i + 1][0] for i in range(len(samples) - 1)):
        raise ValueError(f"{path}: times must be strictly increasing")
    return samples


def read_cd(path):
    return read_coefficients(path, ("Cd",))


def clipped_samples(samples, start, end):
    if samples[0][0] > start or samples[-1][0] < end:
        raise ValueError(
            f"data covers {samples[0][0]:g}–{samples[-1][0]:g} s, "
            f"not the full {start:g}–{end:g} s window"
        )

    def interpolate(time):
        for (ta, ya), (tb, yb) in zip(samples, samples[1:]):
            if ta <= time <= tb:
                return ya + (yb - ya) * (time - ta) / (tb - ta)
        raise ValueError(f"cannot interpolate at {time:g} s")

    clipped = [(start, interpolate(start))]
    clipped.extend((t, y) for t, y in samples if start < t < end)
    clipped.append((end, interpolate(end)))
    return clipped


def weighted_stats(samples, start, end):
    points = clipped_samples(samples, start, end)
    duration = end - start
    area = 0.0
    for (ta, ya), (tb, yb) in zip(points, points[1:]):
        area += (ya + yb) * (tb - ta) / 2.0
    mean = area / duration

    variance_area = 0.0
    for (ta, ya), (tb, yb) in zip(points, points[1:]):
        a = ya - mean
        b = yb - mean
        variance_area += (a * a + a * b + b * b) * (tb - ta) / 3.0
    return mean, math.sqrt(max(0.0, variance_area / duration))


def rising_crossings(samples, start):
    crossings = []
    for (ta, _, ca), (tb, _, cb) in zip(samples, samples[1:]):
        if ca <= 0 < cb:
            crossing = ta if ca == 0 else ta + (tb - ta) * -ca / (cb - ca)
            if crossing >= start:
                crossings.append(crossing)
    return crossings


def summarize_cycles(samples, start, count, case_path):
    crossings = rising_crossings(samples, start)
    if len(crossings) <= count:
        raise ValueError(
            f"{case_path}: found {len(crossings)} rising Cl=0 crossings after {start:g} s; "
            f"need {count + 1} for {count} complete cycles"
        )
    cycles = []
    for index in range(count):
        cycle_start, cycle_end = crossings[index:index + 2]
        mean, _ = weighted_stats(
            [(time, cd) for time, cd, _ in samples], cycle_start, cycle_end
        )
        cycles.append({
            "start_s": cycle_start,
            "end_s": cycle_end,
            "period_s": cycle_end - cycle_start,
            "mean_cd": mean,
        })
    combined, _ = weighted_stats(
        [(time, cd) for time, cd, _ in samples], cycles[0]["start_s"], cycles[-1]["end_s"]
    )
    return cycles, combined


def summarize(case_path, cycle_count=None, cycle_start=WINDOW_START):
    data_path = coefficient_file(case_path)
    if cycle_count is None:
        samples = read_cd(data_path)
    else:
        samples = read_coefficients(data_path, ("Cd", "Cl"))
    cd_samples = [(sample[0], sample[1]) for sample in samples]
    mean, std = weighted_stats(cd_samples, WINDOW_START, WINDOW_END)
    first, first_std = weighted_stats(cd_samples, WINDOW_START, WINDOW_MIDDLE)
    second, second_std = weighted_stats(cd_samples, WINDOW_MIDDLE, WINDOW_END)
    result = {
        "case": str(case_path),
        "data_file": str(data_path),
        "coverage_start_s": cd_samples[0][0],
        "coverage_end_s": cd_samples[-1][0],
        "mean_cd_0.5_1.0": mean,
        "mean_cd_0.5_0.75": first,
        "mean_cd_0.75_1.0": second,
        "std_cd_0.5_1.0": std,
        "std_cd_0.5_0.75": first_std,
        "std_cd_0.75_1.0": second_std,
    }
    if cycle_count is not None:
        cycles, combined = summarize_cycles(samples, cycle_start, cycle_count, case_path)
        result["cycle_mean_cd"] = combined
        for index, cycle in enumerate(cycles, start=1):
            result[f"cycle_{index}_start_s"] = cycle["start_s"]
            result[f"cycle_{index}_end_s"] = cycle["end_s"]
            result[f"cycle_{index}_period_s"] = cycle["period_s"]
            result[f"cycle_{index}_mean_cd"] = cycle["mean_cd"]
    return result


def render_markdown(results):
    baseline = results[0]["mean_cd_0.5_1.0"]
    lines = [
        "| Case | Data coverage (s) | Mean Cd (0.5–1.0 s) | Mean Cd (0.5–0.75 s) | Mean Cd (0.75–1.0 s) | Time-weighted std Cd | Change vs baseline |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        mean = result["mean_cd_0.5_1.0"]
        if baseline == 0:
            change = "—"
        else:
            change = f"{(mean - baseline) / baseline * 100:+.3f}%"
        lines.append(
            f"| {result['case']} | {result['coverage_start_s']:.6g}–{result['coverage_end_s']:.6g} | "
            f"{mean:.8g} | {result['mean_cd_0.5_0.75']:.8g} | "
            f"{result['mean_cd_0.75_1.0']:.8g} | {result['std_cd_0.5_1.0']:.8g} | {change} |"
        )
    output = "\n".join(lines) + "\n"
    if "cycle_mean_cd" in results[0]:
        cycle_lines = [
            "\n| Case | Cycle window (s) | Periods (s) | Individual cycle means Cd | Cycle-averaged Cd | Change vs baseline cycle mean |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for result in results:
            change = result.get("cycle_change_vs_baseline_percent", "")
            indices = []
            index = 1
            while f"cycle_{index}_mean_cd" in result:
                indices.append(index)
                index += 1
            means = ", ".join(f"{result[f'cycle_{index}_mean_cd']:.8g}" for index in indices)
            periods = ", ".join(f"{result[f'cycle_{index}_period_s']:.8g}" for index in indices)
            window_end = result[f"cycle_{indices[-1]}_end_s"]
            cycle_lines.append(
                f"| {result['case']} | {result['cycle_1_start_s']:.8g}–{window_end:.8g} | "
                f"{periods} | {means} | {result['cycle_mean_cd']:.8g} | "
                f"{change:+.3f}% |" if change != "" else
                f"| {result['case']} | {result['cycle_1_start_s']:.8g}–{window_end:.8g} | "
                f"{periods} | {means} | {result['cycle_mean_cd']:.8g} | — |"
            )
        output += "\n".join(cycle_lines) + "\n"
    return output


def render_csv(results):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="+", help="case directories or coefficient.dat files; first case is baseline")
    parser.add_argument("--csv", dest="csv_path", help="write machine-readable results to this CSV file")
    parser.add_argument("--markdown", dest="markdown_path", help="write summary table to this Markdown file")
    parser.add_argument("--cycles", type=int, help="also average the first N complete Cl cycles after --cycle-start")
    parser.add_argument("--cycle-start", type=float, default=WINDOW_START, help="earliest rising Cl=0 crossing to use (default: 0.5 s)")
    args = parser.parse_args()

    try:
        if args.cycles is not None and args.cycles < 1:
            raise ValueError("--cycles must be at least 1")
        results = [summarize(case, args.cycles, args.cycle_start) for case in args.cases]
        baseline = results[0]["mean_cd_0.5_1.0"]
        for result in results:
            result["change_vs_baseline_percent"] = (
                (result["mean_cd_0.5_1.0"] - baseline) / baseline * 100
                if baseline != 0 else ""
            )
        if args.cycles is not None:
            cycle_baseline = results[0]["cycle_mean_cd"]
            for result in results:
                result["cycle_change_vs_baseline_percent"] = (
                    (result["cycle_mean_cd"] - cycle_baseline) / cycle_baseline * 100
                    if cycle_baseline != 0 else ""
                )
        if args.csv_path:
            Path(args.csv_path).write_text(render_csv(results))
        if args.markdown_path:
            Path(args.markdown_path).write_text(render_markdown(results))
        if not args.csv_path:
            print(render_csv(results), end="")
        if not args.markdown_path:
            print(render_markdown(results), end="")
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
