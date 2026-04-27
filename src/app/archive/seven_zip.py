from pathlib import Path
import subprocess


def validate_seven_zip_paths(seven_zip_exe_path: str, seven_zip_fm_path: str) -> list[str]:
    issues: list[str] = []

    exe_path = Path(seven_zip_exe_path)
    if not exe_path.is_file():
        issues.append(f"7-Zip CLI executable not found: {exe_path}")
    else:
        if exe_path.suffix.lower() != ".exe":
            issues.append(f"Unexpected 7-Zip CLI path (expected .exe): {exe_path}")

        result = subprocess.run(
            [str(exe_path), "-h"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            if detail:
                issues.append(f"7-Zip CLI did not run successfully ({exe_path}).\n{detail}")
            else:
                issues.append(f"7-Zip CLI did not run successfully ({exe_path}).")

    fm_path = Path(seven_zip_fm_path)
    if not fm_path.is_file():
        issues.append(f"7-Zip File Manager not found: {fm_path}")

    return issues


def add_files_to_archive(
    seven_zip_exe_path: str,
    archive_path: Path,
    files: list[Path],
    create_archive: bool = False,
    password: str | None = None,
) -> str:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    effective_create_archive = create_archive

    # Save dialogs may pre-create a zero-byte file. 7-Zip treats that as an
    # invalid archive, so remove it and force new archive creation.
    if archive_path.exists() and archive_path.stat().st_size == 0:
        archive_path.unlink()
        effective_create_archive = True

    command = [
        seven_zip_exe_path,
        "a",
        str(archive_path),
        *[str(file_path) for file_path in files],
        "-mhe=on",
    ]
    if password is None:
        command.append("-p")
    else:
        command.append(f"-p{password}")

    if effective_create_archive:
        command.append("-t7z")

    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            raise RuntimeError(f"7-Zip failed with exit code {result.returncode}.\n{detail}")
        raise RuntimeError(f"7-Zip failed with exit code {result.returncode}.")
    return (result.stdout or "").strip()


def extract_archive(
    seven_zip_exe_path: str,
    archive_path: Path,
    output_dir: Path,
    password: str,
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        seven_zip_exe_path,
        "x",
        str(archive_path),
        f"-o{output_dir}",
        f"-p{password}",
        "-y",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            raise RuntimeError(f"7-Zip extract failed with exit code {result.returncode}.\n{detail}")
        raise RuntimeError(f"7-Zip extract failed with exit code {result.returncode}.")
    return (result.stdout or "").strip()


def create_archive_from_directory(
    seven_zip_exe_path: str,
    source_dir: Path,
    archive_path: Path,
    password: str,
) -> str:
    command = [
        seven_zip_exe_path,
        "a",
        str(archive_path),
        str(source_dir / "*"),
        f"-p{password}",
        "-mhe=on",
        "-t7z",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            raise RuntimeError(
                f"7-Zip create-from-directory failed with exit code {result.returncode}.\n{detail}"
            )
        raise RuntimeError(f"7-Zip create-from-directory failed with exit code {result.returncode}.")
    return (result.stdout or "").strip()


def open_archive_in_file_manager(seven_zip_fm_path: str, archive_path: Path) -> None:
    fm_path = Path(seven_zip_fm_path)
    if not fm_path.is_file():
        raise RuntimeError(f"7-Zip File Manager not found at: {fm_path}")

    subprocess.Popen([str(fm_path), str(archive_path)])
