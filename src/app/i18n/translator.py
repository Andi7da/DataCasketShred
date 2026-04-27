import json
import os
from pathlib import Path


class Translator:
    def __init__(self, default_locale: str = "de") -> None:
        self.default_locale = default_locale
        bundled_locales = Path(__file__).parent / "locales"
        user_locales = self._get_user_locale_dir()
        user_locales.mkdir(parents=True, exist_ok=True)

        # Resolution order: user override first, bundled fallback second.
        self._locale_paths = [user_locales, bundled_locales]
        self._cache: dict[str, dict[str, str]] = {}

    def _get_user_locale_dir(self) -> Path:
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "DataCasketShred" / "locales"
        return Path.home() / ".datacasketshred" / "locales"

    def _load_locale(self, locale: str) -> dict[str, str]:
        if locale in self._cache:
            return self._cache[locale]

        merged: dict[str, str] = {}
        for locale_path in self._locale_paths:
            file_path = locale_path / f"{locale}.json"
            if not file_path.exists():
                continue
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # Ignore invalid user overrides and fall back to bundled files.
                continue
            for key, value in data.items():
                if isinstance(value, str):
                    merged[key] = value

        self._cache[locale] = merged
        return self._cache[locale]

    def t(self, key: str, locale: str | None = None, **kwargs: object) -> str:
        active_locale = locale or self.default_locale
        translations = self._load_locale(active_locale)
        fallback_translations = self._load_locale(self.default_locale)

        template = translations.get(key) or fallback_translations.get(key) or key
        return template.format(**kwargs)
