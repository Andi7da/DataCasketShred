import argparse
from getpass import getpass
from pathlib import Path
import sys

from app.archive.seven_zip import add_files_to_archive, validate_seven_zip_paths
from app.config.settings import AppSettings, load_settings
from app.history.secure_delete import delete_file, overwrite_file_with_random_data, secure_delete_file
from app.i18n.translator import Translator
from app.logging.logger import setup_logging
from app.ui.gui import DataCasketShredApp


def bootstrap() -> tuple[AppSettings, Translator]:
    settings = load_settings()
    logger = setup_logging(settings.log_level, settings.log_to_file)
    translator = Translator(default_locale=settings.default_locale)
    logger.info("Application bootstrapped successfully.")
    return settings, translator


def main() -> None:
    settings, translator = bootstrap()
    issues = validate_seven_zip_paths(
        seven_zip_exe_path=settings.seven_zip_exe_path,
        seven_zip_fm_path=settings.seven_zip_fm_path,
    )
    parser = argparse.ArgumentParser(
        description=translator.t("app.description", locale=settings.default_locale)
    )
    parser.add_argument("archive_path", nargs="?", type=Path, help=translator.t("cli.archive_path"))
    parser.add_argument("files", nargs="*", type=Path, help=translator.t("cli.files"))
    parser.add_argument(
        "--create",
        action="store_true",
        help=translator.t("cli.create"),
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run command-line mode instead of GUI.",
    )
    parser.add_argument(
        "--checkshred",
        action="store_true",
        help="Overwrite all files first, pause, then delete them.",
    )
    args = parser.parse_args()

    if not args.cli and args.archive_path is None and not args.files:
        app = DataCasketShredApp(settings=settings, translator=translator, check_shred=args.checkshred)
        app.run()
        return

    if args.archive_path is None:
        raise SystemExit("archive_path is required in CLI mode.")

    if issues:
        print("7-Zip configuration issues:\n", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        print("\nFix SEVEN_ZIP_EXE_PATH / SEVEN_ZIP_FM_PATH in .env and retry.", file=sys.stderr)
        raise SystemExit(2)

    _run_cli(
        settings=settings,
        translator=translator,
        archive_path=args.archive_path,
        files_arg=args.files,
        create=args.create,
        check_shred=args.checkshred,
    )


def _run_cli(
    settings: AppSettings,
    translator: Translator,
    archive_path: Path,
    files_arg: list[Path],
    create: bool,
    check_shred: bool,
) -> None:
    logger = setup_logging(settings.log_level, settings.log_to_file)
    files = [path for path in files_arg if path.is_file()]
    missing = [path for path in files_arg if not path.is_file()]

    if not files:
        logger.error(translator.t("error.no_valid_files", locale=settings.default_locale))
        raise SystemExit(2)

    for missing_path in missing:
        logger.warning(
            translator.t("warn.skipping_path", locale=settings.default_locale, path=missing_path)
        )

    password = getpass("Archive password (hidden): ")

    try:
        add_files_to_archive(
            seven_zip_exe_path=settings.seven_zip_exe_path,
            archive_path=archive_path,
            files=files,
            create_archive=create,
            password=password,
        )
    except RuntimeError as error:
        logger.error(str(error))
        raise SystemExit(1) from error

    if check_shred:
        for file_path in files:
            overwrite_file_with_random_data(file_path=file_path, passes=settings.shred_passes)

        input(
            "CheckShred mode: all selected files were overwritten with random data.\n"
            "Inspect if needed, then press Enter to permanently delete them."
        )

        for file_path in files:
            delete_file(file_path=file_path)
            logger.info(
                translator.t("info.deleted_file", locale=settings.default_locale, path=file_path)
            )
    else:
        for file_path in files:
            secure_delete_file(file_path=file_path, passes=settings.shred_passes)
            logger.info(
                translator.t("info.deleted_file", locale=settings.default_locale, path=file_path)
            )

    logger.info(translator.t("info.done", locale=settings.default_locale))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
