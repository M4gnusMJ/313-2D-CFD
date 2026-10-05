#!/usr/bin/env python3
"""Save each completed 313 study case in a separate compressed archive."""

import tarfile
import fcntl
from pathlib import Path

from report_results import load_study_manifest
from run_study import OUTPUT, case_complete


def main():
    manifest = load_study_manifest()
    archives = OUTPUT / "archives"
    archives.mkdir(exist_ok=True)
    for name, state in manifest["cases"].items():
        status = state.get("status")
        if status not in ("complete", "failed"):
            continue
        case_dir = OUTPUT / name
        if status == "complete":
            complete, message = case_complete(state, case_dir)
            if not complete:
                raise RuntimeError(f"{name}: {message}")
        elif not (case_dir / "log.pimpleFoam").is_file():
            continue
        suffix = ".failed" if status == "failed" else ""
        target = archives / f"{name}{suffix}.tar.gz"
        if target.exists():
            print(f"{name}: archive already saved")
            continue
        temporary = target.with_name(target.name + ".tmp")

        def exclude_cache(info):
            return None if "dynamicCode" in Path(info.name).parts else info

        with tarfile.open(temporary, "w:gz") as archive:
            archive.add(case_dir, arcname=name, filter=exclude_cache)
        temporary.replace(target)
        with tarfile.open(target, "r:gz") as archive:
            assert f"{name}/log.pimpleFoam" in archive.getnames()
        print(f"{name}: saved {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    with (OUTPUT / "archives.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        main()
