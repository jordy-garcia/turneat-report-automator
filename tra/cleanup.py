import os
import shutil
from pathlib import Path


def clear_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name in os.listdir(path):
        entry = path / name
        try:
            if entry.is_file() or entry.is_symlink():
                entry.unlink()
            elif entry.is_dir():
                shutil.rmtree(entry)
        except OSError as exc:
            print(f"WARNING: Could not delete {entry}: {exc}")


def prepare_output_dirs(debug_dir: Path, reports_dir: Path) -> None:
    clear_directory(debug_dir)
    clear_directory(reports_dir)
