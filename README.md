# DataCasketShred

DataCasketShred packs one or more files into a password-protected `7z` archive and securely deletes originals in a separate step.

## Core behavior

- calls `7z.exe` to add files to an archive
- prompts for archive password in the app (GUI) or hidden prompt (CLI)
- enables header encryption (`-mhe=on`) so file names are hidden
- remembers last used archive and source folder
- supports separate shredding step after archive confirmation
- optional `7zFM.exe` integration for visual archive inspection
- supports archive password change workflow via temporary local extraction

## Configuration

Use `.env` (loaded automatically on startup from the project root):

- `APP_NAME=DataCasketShred`
- `SEVEN_ZIP_EXE_PATH=C:\Program Files\7-Zip\7z.exe`
- `SEVEN_ZIP_FM_PATH=C:\Program Files\7-Zip\7zFM.exe`
- `SHRED_PASSES=1` (number of overwrite passes)
- `DEFAULT_LOCALE=en`
- `LOG_LEVEL=INFO`

## Locale overrides (user contributed)

User-local locale files can override bundled translations:

- `%LOCALAPPDATA%\DataCasketShred\locales\en.json`
- `%LOCALAPPDATA%\DataCasketShred\locales\de.json`

If a key exists in the user file, it wins over bundled defaults. Invalid JSON is ignored and bundled texts are used.

## Quick start (Windows / PowerShell)

1. Run `.\scripts\bootstrap.ps1`
2. Activate venv with `.\.venv\Scripts\Activate.ps1`
3. Start GUI: `python -m app.main`
4. Workflow in GUI:
   - choose file(s)
   - choose/create archive
   - click `Einpacken`
   - optional `7z ansehen` (opens `7zFM.exe` for password + browsing)
   - click `Temporäre Daten shreddern`

## Python environment best practice

Use project-local Python from `.venv`, not your global Python.

- Do: `.\scripts\tasks.ps1 -Task run`
- Do: `.\scripts\tasks.ps1 -Task test`
- Do: `.\.venv\Scripts\python.exe -m app.main`
- Do not: `python -m app.main` without activated `.venv`

`.\.venv\Scripts\Activate.ps1` updates your current terminal session so `python` and `pip`
point to `.venv` first. It does not change system-wide settings.

## Test runs (conventional)

Preferred for this project:

- all tests: `.\scripts\tasks.ps1 -Task test`

Direct pytest (also fine):

- all tests: `.\.venv\Scripts\python.exe -m pytest -q`
- one file: `.\.venv\Scripts\python.exe -m pytest -q tests\test_smoke.py`
- one test: `.\.venv\Scripts\python.exe -m pytest -q tests\test_smoke.py::test_settings_loads_defaults`

## Check shred mode

For manual verification while testing:

- GUI mode: `python -m app.main --checkshred`
- CLI mode: `python -m app.main --cli --checkshred "D:\Vault\myvault.7z" "D:\Source\a.txt"`

In check mode, all selected files are overwritten first, then you get one confirmation step
before permanent deletion.

## Drag and drop idea

You can create a shortcut to run the tool with a fixed archive path and then drop files onto it.

Example target:

`powershell -NoProfile -Command "cd 'C:\Users\andim\Prg_Cursor\Tools\DataCasketShred'; .\.venv\Scripts\python.exe -m app.main --cli 'D:\Vault\myvault.7z' %*"`

## Scripts

- `.\scripts\bootstrap.ps1` -> setup `.venv`, install dependencies, create `.env` if missing
- `.\scripts\tasks.ps1 -Task test` -> run tests
- `.\scripts\tasks.ps1 -Task build-exe` -> build onefile windowed exe via PyInstaller (includes locale files via `--add-data`)

### Build exe variants

- default: `.\scripts\tasks.ps1 -Task build-exe`
- with console window: `.\scripts\tasks.ps1 -Task build-exe -- -NoWindowed`
- one-dir build: `.\scripts\tasks.ps1 -Task build-exe -- -NoOneFile`

## Learning docs

- `D:\Users\andim\Prg_Cursor\AM_Doku\docupython.md` -> practical best practices and recurring workflows
