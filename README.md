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
./Allrun prism moon
./Allrun                  # Runs prism, moon, and 313 in sequence
```

Each selected geometry must exist at `geometries/<name>/body.stl`.

Edit `base_setup/` for changes shared by future preparations. Directly running
a generated case uses its existing copied settings.
