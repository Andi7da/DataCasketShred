from __future__ import annotations

from pathlib import Path
import shutil
import tkinter as tk
import tkinter.scrolledtext as tk_scrolledtext
from tkinter import filedialog

from app.archive.seven_zip import (
    add_files_to_archive,
    create_archive_from_directory,
    extract_archive,
    open_archive_in_file_manager,
    validate_seven_zip_paths,
)
from app.config.settings import AppSettings
from app.history.secure_delete import delete_file, overwrite_file_with_random_data
from app.i18n.translator import Translator
from app.state.store import AppState, load_state, save_state


class DataCasketShredApp:
    def __init__(self, settings: AppSettings, translator: Translator, check_shred: bool = False) -> None:
        self.settings = settings
        self.translator = translator
        self.check_shred = check_shred
        self.state = load_state()

        self.root = tk.Tk()
        self.root.title(settings.app_name)
        self.root.geometry("820x560")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.archive_path_var = tk.StringVar(value=self.state.last_archive_path)
        self.selected_files: list[Path] = []
        self.pending_shred_files: list[Path] = []

        self._build_ui()
        self._validate_7zip_on_startup()

    def _t(self, key: str, **kwargs: object) -> str:
        return self.translator.t(key, locale=self.settings.default_locale, **kwargs)

    def _validate_7zip_on_startup(self) -> None:
        issues = validate_seven_zip_paths(
            seven_zip_exe_path=self.settings.seven_zip_exe_path,
            seven_zip_fm_path=self.settings.seven_zip_fm_path,
        )
        if not issues:
            return

        message = "\n\n".join(issues)
        message += f"\n\n{self._t('gui.error.seven_zip_env_hint')}"
        self._show_error(self._t("gui.dialog.title_7zip_config"), message)

    def _center_window(self, window: tk.Toplevel, width: int, height: int) -> None:
        self.root.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()

        x = parent_x + max(0, (parent_w - width) // 2)
        y = parent_y + max(0, (parent_h - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def _prepare_native_dialog(self) -> None:
        # Tk's filedialog is a native OS dialog. We cannot reliably center it like a Tk Toplevel,
        # but we can make the owning window active so the dialog tends to appear with it.
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            self.root.update_idletasks()
        finally:
            self.root.attributes("-topmost", False)

    def _show_dialog(
        self,
        title: str,
        message: str,
        buttons: list[str],
        input_default: str | None = None,
        password_input: bool = False,
        width: int = 400,
        height: int = 300,
    ) -> tuple[int, str | None]:
        result: dict[str, int | str | None] = {"button": -1, "input": None}

        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.minsize(380, 260)

        container = tk.Frame(dialog, padx=12, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        text_area = tk_scrolledtext.ScrolledText(container, wrap=tk.WORD, height=10)
        text_area.pack(fill=tk.BOTH, expand=True)
        text_area.insert("1.0", message)
        text_area.configure(state=tk.DISABLED)

        input_var = tk.StringVar(value=input_default or "")
        input_entry: tk.Entry | None = None
        if input_default is not None:
            input_entry = tk.Entry(container, textvariable=input_var, show="*" if password_input else "")
            input_entry.pack(fill=tk.X, pady=(10, 0))

        buttons_frame = tk.Frame(container)
        buttons_frame.pack(fill=tk.X, pady=(12, 0))

        def make_button_handler(index: int):
            def _on_click() -> None:
                result["button"] = index
                if input_entry is not None:
                    result["input"] = input_var.get()
                dialog.destroy()

            return _on_click

        for idx, label in enumerate(buttons, start=1):
            tk.Button(
                buttons_frame,
                text=label,
                width=11,
                command=make_button_handler(idx),
            ).pack(side=tk.RIGHT, padx=(6, 0))

        def on_close() -> None:
            result["button"] = -1
            if input_entry is not None:
                result["input"] = None
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)
        dialog.bind("<Escape>", lambda _event: on_close())
        if buttons:
            dialog.bind("<Return>", lambda _event: make_button_handler(1)())

        self._center_window(dialog, width, height)
        if input_entry is not None:
            input_entry.focus_set()
        dialog.wait_window()

        return int(result["button"]), result["input"] if isinstance(result["input"], str) else None

    def _show_info(self, title: str, message: str) -> None:
        self._show_dialog(title=title, message=message, buttons=[self._t("gui.ok")], width=400, height=300)

    def _show_error(self, title: str, message: str) -> None:
        self._show_info(title, message)

    def _ask_yes_no(self, title: str, message: str) -> bool:
        button, _ = self._show_dialog(
            title=title,
            message=message,
            buttons=[self._t("gui.yes"), self._t("gui.no")],
            width=400,
            height=300,
        )
        return button == 1

    def _ask_yes_no_cancel(self, title: str, message: str) -> bool | None:
        button, _ = self._show_dialog(
            title=title,
            message=message,
            buttons=[self._t("gui.yes"), self._t("gui.no"), self._t("gui.cancel")],
            width=420,
            height=320,
        )
        if button == 1:
            return True
        if button == 2:
            return False
        return None

    def _ask_password(self, title: str, message: str) -> str | None:
        button, value = self._show_dialog(
            title=title,
            message=message,
            buttons=[self._t("gui.ok"), self._t("gui.cancel")],
            input_default="",
            password_input=True,
            width=400,
            height=300,
        )
        if button != 1:
            return None
        return value if value is not None else ""

    def _ask_password_change_values(self) -> tuple[str, str, str] | None:
        result: dict[str, tuple[str, str, str] | None] = {"value": None}

        dialog = tk.Toplevel(self.root)
        dialog.title(self._t("gui.dialog.title_password_change"))
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = tk.Frame(dialog, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        old_var = tk.StringVar()
        new_var = tk.StringVar()
        repeat_var = tk.StringVar()

        tk.Label(frame, text=self._t("gui.password.prompt_old"), justify=tk.LEFT, wraplength=420).pack(anchor=tk.W)
        old_entry = tk.Entry(frame, textvariable=old_var, show="*")
        old_entry.pack(fill=tk.X, pady=(6, 8))

        tk.Label(frame, text=self._t("gui.password.prompt_new"), justify=tk.LEFT, wraplength=420).pack(anchor=tk.W)
        new_entry = tk.Entry(frame, textvariable=new_var, show="*")
        new_entry.pack(fill=tk.X, pady=(6, 8))

        tk.Label(frame, text=self._t("gui.password.prompt_new_repeat"), justify=tk.LEFT, wraplength=420).pack(
            anchor=tk.W
        )
        repeat_entry = tk.Entry(frame, textvariable=repeat_var, show="*")
        repeat_entry.pack(fill=tk.X, pady=(6, 0))

        buttons = tk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(12, 0))

        def on_ok() -> None:
            result["value"] = (old_var.get(), new_var.get(), repeat_var.get())
            dialog.destroy()

        def on_cancel() -> None:
            result["value"] = None
            dialog.destroy()

        dialog.bind("<Return>", lambda _event: on_ok())
        dialog.bind("<Escape>", lambda _event: on_cancel())

        tk.Button(buttons, text=self._t("gui.cancel"), width=10, command=on_cancel).pack(side=tk.RIGHT)
        tk.Button(buttons, text=self._t("gui.ok"), width=10, command=on_ok).pack(side=tk.RIGHT, padx=(6, 0))

        self._center_window(dialog, 500, 300)
        old_entry.focus_set()
        dialog.wait_window()
        return result["value"]

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        archive_frame = tk.LabelFrame(frame, text=self._t("gui.section.target_archive"), padx=8, pady=8)
        archive_frame.pack(fill=tk.X, pady=(0, 8))

        archive_entry = tk.Entry(archive_frame, textvariable=self.archive_path_var)
        archive_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        tk.Button(archive_frame, text=self._t("gui.button.choose_7z"), command=self._choose_archive).pack(side=tk.LEFT)
        tk.Button(archive_frame, text=self._t("gui.button.new_7z"), command=self._create_archive_path).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        file_frame = tk.LabelFrame(frame, text=self._t("gui.section.files_to_pack"), padx=8, pady=8)
        file_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        list_wrapper = tk.Frame(file_frame)
        list_wrapper.pack(fill=tk.BOTH, expand=True)

        self.file_listbox = tk.Listbox(list_wrapper, selectmode=tk.EXTENDED)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = tk.Scrollbar(list_wrapper, command=self.file_listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scroll.set)

        controls = tk.Frame(file_frame)
        controls.pack(fill=tk.X, pady=(8, 0))
        tk.Button(controls, text=self._t("gui.button.choose_files"), command=self._choose_files).pack(side=tk.LEFT)
        tk.Button(controls, text=self._t("gui.button.remove_selection"), command=self._remove_selected_files).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        tk.Button(controls, text=self._t("gui.button.clear_list"), command=self._clear_selected_files).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        action_frame = tk.Frame(frame)
        action_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Button(action_frame, text=self._t("gui.button.pack"), command=self._pack_files).pack(side=tk.LEFT)
        tk.Button(action_frame, text=self._t("gui.button.view_7z"), command=self._inspect_archive).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        tk.Button(
            action_frame,
            text=self._t("gui.button.change_password"),
            command=self._change_archive_password,
        ).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(
            action_frame,
            text=self._t("gui.button.shred_temp"),
            command=self._shred_pending_files,
        ).pack(side=tk.LEFT, padx=(6, 0))

        output_frame = tk.LabelFrame(frame, text=self._t("gui.section.output"), padx=8, pady=8)
        output_frame.pack(fill=tk.BOTH, expand=True)
        self.output_text = tk.Text(output_frame, height=12, wrap=tk.NONE)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        self._append_output(self._t("gui.ready_hint"))

    def run(self) -> None:
        self.root.mainloop()

    def _choose_archive(self) -> None:
        self._prepare_native_dialog()
        start_file = self.archive_path_var.get() or self.state.last_archive_path
        selected = filedialog.askopenfilename(
            title=self._t("gui.filedialog.title.choose_7z"),
            filetypes=[("7z archive", "*.7z"), ("All files", "*.*")],
            initialfile=Path(start_file).name if start_file else "",
            initialdir=str(Path(start_file).parent) if start_file else None,
            parent=self.root,
        )
        if not selected:
            return
        self.archive_path_var.set(selected)
        self._save_state(last_archive_path=selected)

    def _create_archive_path(self) -> None:
        self._prepare_native_dialog()
        start_file = self.archive_path_var.get() or self.state.last_archive_path
        selected = filedialog.asksaveasfilename(
            title=self._t("gui.filedialog.title.new_7z"),
            defaultextension=".7z",
            filetypes=[("7z archive", "*.7z"), ("All files", "*.*")],
            initialfile=Path(start_file).name if start_file else "backup.7z",
            initialdir=str(Path(start_file).parent) if start_file else None,
            parent=self.root,
        )
        if not selected:
            return
        self.archive_path_var.set(selected)
        self._save_state(last_archive_path=selected)

    def _choose_files(self) -> None:
        self._prepare_native_dialog()
        initial_dir = self.state.last_source_dir if self.state.last_source_dir else None
        files = filedialog.askopenfilenames(
            title=self._t("gui.filedialog.title.choose_files"),
            initialdir=initial_dir,
            parent=self.root,
        )
        if not files:
            return

        for file_name in files:
            path = Path(file_name)
            if path not in self.selected_files and path.is_file():
                self.selected_files.append(path)
                self.file_listbox.insert(tk.END, str(path))

        self._save_state(last_source_dir=str(Path(files[0]).parent))
        self._append_output(self._t("gui.output.files_added", count=len(files)))

    def _remove_selected_files(self) -> None:
        indexes = list(self.file_listbox.curselection())
        if not indexes:
            return
        for index in reversed(indexes):
            self.file_listbox.delete(index)
            self.selected_files.pop(index)

    def _clear_selected_files(self) -> None:
        self.selected_files = []
        self.file_listbox.delete(0, tk.END)

    def _pack_files(self) -> None:
        archive_path = Path(self.archive_path_var.get().strip()) if self.archive_path_var.get().strip() else None
        if archive_path is None:
            self._show_error(self._t("gui.dialog.title_error"), self._t("gui.error.select_target_first"))
            return
        if not self.selected_files:
            self._show_error(self._t("gui.dialog.title_error"), self._t("gui.error.select_files_first"))
            return

        files = [path for path in self.selected_files if path.is_file()]
        if not files:
            self._show_error(self._t("gui.dialog.title_error"), self._t("gui.error.no_valid_selected_files"))
            return

        create_archive = not archive_path.exists()
        password = self._ask_password(
            self._t("gui.dialog.title_password"),
            self._t("gui.password.prompt_pack"),
        )
        if password is None:
            return
        if not password.strip():
            self._show_error(self._t("gui.dialog.title_error"), self._t("gui.error.password_empty"))
            return

        try:
            pack_output = add_files_to_archive(
                seven_zip_exe_path=self.settings.seven_zip_exe_path,
                archive_path=archive_path,
                files=files,
                create_archive=create_archive,
                password=password,
            )
        except RuntimeError as error:
            self._show_error(self._t("gui.dialog.title_7zip_error"), str(error))
            return

        self.pending_shred_files = files.copy()
        self._save_state(last_archive_path=str(archive_path))
        self._append_output(self._t("gui.output.packed_ready_shred", count=len(files)))
        if pack_output:
            self._append_output(pack_output)
        self._show_info(
            self._t("gui.dialog.title_pack_done"),
            self._t("gui.pack_done.message"),
        )

    def _inspect_archive(self) -> None:
        archive_path_text = self.archive_path_var.get().strip()
        if not archive_path_text:
            self._show_error(self._t("gui.dialog.title_error"), self._t("gui.error.select_target_first"))
            return
        archive_path = Path(archive_path_text)
        if not archive_path.exists():
            self._show_error(self._t("gui.dialog.title_error"), self._t("gui.error.archive_missing"))
            return

        try:
            open_archive_in_file_manager(self.settings.seven_zip_fm_path, archive_path)
        except RuntimeError as error:
            self._show_error(self._t("gui.dialog.title_7zip_error"), str(error))
            return

        self._append_output(self._t("gui.output.started_7zfm", path=str(archive_path)))

    def _shred_and_remove_temp_dir(self, temp_root: Path) -> None:
        files = [path for path in temp_root.rglob("*") if path.is_file()]
        overwritten_paths: list[Path] = []
        for file_path in files:
            overwrite_file_with_random_data(file_path=file_path, passes=self.settings.shred_passes)
            overwritten_paths.append(file_path)

        if self.check_shred and overwritten_paths:
            preview = "\n".join(str(path) for path in overwritten_paths[:25])
            if len(overwritten_paths) > 25:
                preview += "\n" + self._t("gui.checkshred.more_files", count=len(overwritten_paths) - 25)

            should_delete = self._ask_yes_no(
                self._t("gui.dialog.title_checkshred"),
                self._t("gui.checkshred.message", preview=preview),
            )
            if not should_delete:
                raise RuntimeError("Temp shredding paused by user in CheckShred mode.")

        for file_path in overwritten_paths:
            delete_file(file_path=file_path)

        # Remaining directories can be removed normally after all files are gone.
        if temp_root.exists():
            shutil.rmtree(temp_root, ignore_errors=False)

    def _change_archive_password(self) -> None:
        archive_path_text = self.archive_path_var.get().strip()
        if not archive_path_text:
            self._show_error(self._t("gui.dialog.title_error"), self._t("gui.error.select_target_first"))
            return

        archive_path = Path(archive_path_text)
        if not archive_path.exists():
            self._show_error(self._t("gui.dialog.title_error"), self._t("gui.error.archive_missing"))
            return

        password_values = self._ask_password_change_values()
        if password_values is None:
            return
        old_password, new_password, new_password_repeat = password_values

        if not old_password.strip():
            self._show_error(
                self._t("gui.dialog.title_error"),
                self._t("gui.error.password_empty"),
            )
            return
        if not new_password.strip() or not new_password_repeat.strip():
            self._show_error(
                self._t("gui.dialog.title_error"),
                self._t("gui.error.password_empty"),
            )
            return

        if new_password != new_password_repeat:
            self._show_error(
                self._t("gui.dialog.title_error"),
                self._t("gui.error.new_password_mismatch"),
            )
            return

        self._append_output(self._t("gui.output.password_change_start"))

        temp_root = archive_path.parent / "DataCasketShredTemp"
        if temp_root.exists() and any(temp_root.iterdir()):
            self._append_output(self._t("gui.error.temp_dir_exists", path=str(temp_root)))
            return
        temp_root.mkdir(parents=True, exist_ok=True)
        self._append_output(self._t("gui.output.temp_dir", path=str(temp_root)))

        extracted_dir = temp_root / "extracted"
        new_archive_path = archive_path.with_name(f"{archive_path.stem}-new{archive_path.suffix}")
        old_archive_path = archive_path.with_name(f"{archive_path.stem}-old{archive_path.suffix}")

        try:
            if new_archive_path.exists():
                should_delete_new = self._ask_yes_no(
                    self._t("gui.dialog.title_existing_old"),
                    self._t("gui.confirm.delete_existing_new", path=str(new_archive_path)),
                )
                if not should_delete_new:
                    self._append_output(self._t("gui.output.password_change_aborted_existing_new"))
                    return
                new_archive_path.unlink()

            extract_output = extract_archive(
                seven_zip_exe_path=self.settings.seven_zip_exe_path,
                archive_path=archive_path,
                output_dir=extracted_dir,
                password=old_password,
            )
            if extract_output:
                self._append_output(extract_output)
            self._append_output(self._t("gui.output.extract_ok"))

            repack_output = create_archive_from_directory(
                seven_zip_exe_path=self.settings.seven_zip_exe_path,
                source_dir=extracted_dir,
                archive_path=new_archive_path,
                password=new_password,
            )
            if repack_output:
                self._append_output(repack_output)
            self._append_output(self._t("gui.output.repack_ok"))

            if old_archive_path.exists():
                should_delete = self._ask_yes_no(
                    self._t("gui.dialog.title_existing_old"),
                    self._t("gui.confirm.delete_existing_old", path=str(old_archive_path)),
                )
                if not should_delete:
                    self._append_output(self._t("gui.output.password_change_aborted_existing_old"))
                    return
                old_archive_path.unlink()

            self._shred_and_remove_temp_dir(temp_root)
            self._append_output(self._t("gui.output.temp_cleanup_ok"))

            archive_path.rename(old_archive_path)
            self._append_output(self._t("gui.output.rename_old", path=str(old_archive_path)))
            new_archive_path.rename(archive_path)
            self._append_output(self._t("gui.output.rename_new", path=str(archive_path)))
            self._append_output(self._t("gui.output.password_change_done"))
        except Exception as error:
            self._append_output(self._t("gui.output.password_change_failed", error=str(error)))

    def _shred_pending_files(self) -> None:
        if not self.pending_shred_files:
            self._show_info(self._t("gui.dialog.title_info"), self._t("gui.hint.no_pending_shred"))
            return

        if not self._ask_yes_no(
            self._t("gui.dialog.title_confirm"),
            self._t("gui.confirm.shred", count=len(self.pending_shred_files)),
        ):
            return

        deleted = 0
        overwritten_paths: list[Path] = []
        for file_path in self.pending_shred_files:
            if not file_path.exists():
                continue
            overwrite_file_with_random_data(file_path, passes=self.settings.shred_passes)
            overwritten_paths.append(file_path)

        if self.check_shred and overwritten_paths:
            preview = "\n".join(str(path) for path in overwritten_paths[:25])
            if len(overwritten_paths) > 25:
                preview += "\n" + self._t("gui.checkshred.more_files", count=len(overwritten_paths) - 25)

            self._show_info(
                self._t("gui.dialog.title_checkshred"),
                self._t("gui.checkshred.message", preview=preview),
            )

        for file_path in overwritten_paths:
            delete_file(file_path)
            deleted += 1
            self._append_output(self.translator.t("info.deleted_file", locale=self.settings.default_locale, path=file_path))

        self.pending_shred_files = []
        self._clear_selected_files()
        self._show_info(self._t("gui.dialog.title_done"), self._t("gui.done.shred_deleted", count=deleted))

    def _on_close(self) -> None:
        if self.pending_shred_files:
            answer = self._ask_yes_no_cancel(
                self._t("gui.dialog.title_not_shredded"),
                self._t("gui.not_shredded.prompt"),
            )
            if answer is None:
                return
            if answer:
                self._shred_pending_files()
                if self.pending_shred_files:
                    return
        self.root.destroy()

    def _save_state(self, last_archive_path: str | None = None, last_source_dir: str | None = None) -> None:
        if last_archive_path is not None:
            self.state.last_archive_path = last_archive_path
        if last_source_dir is not None:
            self.state.last_source_dir = last_source_dir
        save_state(self.state)

    def _append_output(self, text: str) -> None:
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)
