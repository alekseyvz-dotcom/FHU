# config.py
import os
import yaml

DEFAULT_CONFIG = {
    "telegram": {"token": "", "chat_id": ""},
    "storage": {"excel_path": "data/incidents.xlsx"},
    "ui": {"default_duty": ""}
}

def load_config(path: str = "config.yaml"):
    if not os.path.exists(path):
        # Создадим шаблон, чтобы удобнее было редактировать
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(DEFAULT_CONFIG, f, allow_unicode=True, sort_keys=False)
        return DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    # Подставим значения по умолчанию, если чего-то нет
    def deep_merge(a, b):
        for k, v in b.items():
            if isinstance(v, dict):
                a[k] = deep_merge(a.get(k, {}) if isinstance(a.get(k), dict) else {}, v)
            else:
                a.setdefault(k, v)
        return a
    return deep_merge(cfg, DEFAULT_CONFIG)
