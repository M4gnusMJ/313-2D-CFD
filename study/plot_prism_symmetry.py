#!/usr/bin/env python3
"""Compare symmetry and original prism drag histories."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze import coefficient_file, read_coefficients
from run_study import ROOT


fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
for case, label in ((ROOT / "saved_runs/prism_pimple_run", "Original prism"),
                    (ROOT / "runs/prism_symmetry_check/case", "symmetric free-stream condition"),
                    (ROOT / "runs/prism_sa_check/case", "Spalart–Allmaras")):
    samples = read_coefficients(coefficient_file(case), ("Cd",))
    time, cd = zip(*samples)
    ax.plot(time, cd, label=label, linewidth=1.6)
ax.axhline(y=1.55, linestyle="--", label= "Reference value")
ax.set(xlabel="Time (s)", ylabel=r"$C_D$", xlim=(0, 1), ylim=(1, 5))
ax.set_title("Prism drag coefficient comparison")
ax.legend()
ax.grid(alpha=0.25)
output = ROOT / "runs/prism_symmetry_check"
for extension in ("png", "pdf"):
    path = output / f"cd_comparison.{extension}"
    fig.savefig(path, dpi=180)
    print(path)
plt.close(fig)
