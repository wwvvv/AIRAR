from pathlib import Path
import importlib.util
import json
import tempfile

SOURCE = Path(__file__).parents[1] / "src" / "airar.py"
spec = importlib.util.spec_from_file_location("airar_defaults", SOURCE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

EXPECTED_PASSWORDS = ["小猫喝奶啤", "猫里奥小新", "acgyxj.xyz"]
EXPECTED_AD_RULES = ["*收藏*", "*翻译工具*", "*免责声明*", "*点我*", "*TG群*", "*推广*", "网址*", "*.url"]


def load_from(path: Path):
    app = module.SmartUnpackerGUI.__new__(module.SmartUnpackerGUI)
    app.settings_path = path
    return app.load_settings()


def test_fresh_install_defaults():
    with tempfile.TemporaryDirectory() as temp:
        settings = load_from(Path(temp) / "settings.json")
        assert module.APP_VERSION == "2.3.3"
        assert settings["passwords"] == EXPECTED_PASSWORDS
        assert settings["ad_rules"] == EXPECTED_AD_RULES


def test_upgrade_merges_defaults_without_losing_user_rules():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "settings.json"
        path.write_text(json.dumps({
            "passwords": ["我的密码", "猫里奥小新"],
            "ad_rules": ["广告*", "*推广*"],
        }, ensure_ascii=False), encoding="utf-8")
        settings = load_from(path)
        assert settings["passwords"] == EXPECTED_PASSWORDS + ["我的密码"]
        assert settings["ad_rules"] == EXPECTED_AD_RULES + ["广告*"]


if __name__ == "__main__":
    test_fresh_install_defaults()
    test_upgrade_merges_defaults_without_losing_user_rules()
    print("fresh_defaults=OK version=2.3.3")
    print("upgrade_merge=OK user_rules_preserved=True")
