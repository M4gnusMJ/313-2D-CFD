# OpenFOAM cases

Use an active OpenFOAM v2412 environment. Cases use six MPI processes, as set
in `base_setup/system/decomposeParDict.6`.

## Layout

```text
base_setup/             Shared case inputs and per-case Allrun
geometries/<name>/body.stl
runs/<name>_run/        Generated case, including its own Allrun
Allrun                 Copies inputs and runs selected cases
```

All cases receive the same `snappyHexMeshDict` and other base settings.
Only the geometry is selected separately. Generated cases are ignored by Git.

## Geometry preparation: prism and half-moon

Our coordinate convention is X along the flow, Y vertical, and Z spanwise.
The original STL heights are 1000 coordinate units, along their original Z
axis. Convert these millimetre-sized coordinates to metres with a factor of
`0.001`, then scale proportionally by `1.09585` to obtain a height of
`1.09585 m`. The combined uniform scale is `0.00109585`.

In ParaView, starting from each original, unscaled STL:

1. Keep a separate copy of the original STL before replacing `body.stl`.
2. Open the original STL and click **Apply**.
3. Select it in the Pipeline Browser and choose
   **Filters > Alphabetical > Transform**.
4. Set **Scale** to `(0.00109585, 0.00109585, 0.00109585)`,
   **Rotate** to `(-90, 0, 0)` degrees, and **Translate** to `(0, 0, 0)`.
5. Click **Apply**. Select the Transform output and check its bounds in
   **View > Information**.
6. With the Transform output selected, use **File > Save Data** to export
   an STL as `geometries/<name>/body.stl`.

Scaling is uniform, preserving each shape's proportions. The -90 degree
rotation about X makes the original positive Z axis the new positive Y axis.
The coordinate mapping is `(x, y, z) -> (s*x, s*z, -s*y)`, with
`s = 0.00109585`. No translation is included in this preparation step.

Expected dimensions after preparation:

| Geometry | X: length (m) | Y: height (m) | Z: depth (m) |
|---|---:|---:|---:|
| Prism | 1.09585 | 1.09585 | 0.109585 |
| Half-moon | 0.547925 | 1.09585 | 0.109585 |

Both should have Y bounds `0 ... 1.09585` and Z bounds `-0.109585 ... 0`.
These instructions describe the intended preparation; `Allrun` copies the
saved STL as-is and does not apply any scaling or rotation. Apply this
transformation only once to the original geometry.

## Run one case

Put the geometry at `geometries/prism/body.stl`, then run from the project root:

```sh
./Allrun prism
```

This copies the base and geometry into `runs/prism_run/`, then executes that
case's `Allrun`. Replace `prism` with another geometry folder name as needed.

To run an already prepared case directly:

```sh
./runs/prism_run/Allrun
```

## Run several cases

```sh
./Allrun prism half_moon
./Allrun                  # Runs prism and half_moon in sequence
```

Each selected geometry must exist at `geometries/<name>/body.stl`.

Edit `base_setup/` for changes shared by future preparations. Directly running
a generated case uses its existing copied settings.
