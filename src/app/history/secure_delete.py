from pathlib import Path
import os
import secrets


def overwrite_file_with_random_data(file_path: Path, passes: int = 1) -> None:
    if passes < 1:
        raise ValueError("passes must be at least 1")
    if not file_path.exists():
        return
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    file_size = file_path.stat().st_size
    chunk_size = 1024 * 1024

    for _ in range(passes):
        with file_path.open("r+b") as handle:
            remaining = file_size
            while remaining > 0:
                write_size = min(chunk_size, remaining)
                handle.write(secrets.token_bytes(write_size))
                remaining -= write_size
            handle.flush()
            os.fsync(handle.fileno())


def delete_file(file_path: Path) -> None:
    if file_path.exists() and file_path.is_file():
        file_path.unlink()


def secure_delete_file(file_path: Path, passes: int = 1) -> None:
    overwrite_file_with_random_data(file_path=file_path, passes=passes)
    file_path.unlink()
