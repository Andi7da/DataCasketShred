from app.config.settings import load_settings
from app.i18n.translator import Translator


def test_settings_loads_defaults() -> None:
    settings = load_settings()
    assert settings.app_name
    assert settings.log_level
    assert settings.seven_zip_exe_path
    assert settings.seven_zip_fm_path
    assert settings.shred_passes >= 1


def test_translator_returns_text() -> None:
    translator = Translator(default_locale="de")
    text = translator.t("app.welcome")
    assert isinstance(text, str)
    assert text
