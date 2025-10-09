import os
from pathlib import Path


def get_project_root() -> str:
    current = Path(__file__).resolve().parent.parent.parent.parent
    while current.parent != current:
        if (current / "requirements.txt").exists() or (current / "main.py").exists():
            return str(current)
        current = current.parent
    return str(Path(__file__).resolve().parent.parent.parent.parent)


def get_data_dir() -> str:
    return os.path.join(get_project_root(), "data")


def get_config_file() -> str:
    """Get the default config file path"""
    return os.path.join(get_data_dir(), "config.json")


def get_extension_config_file() -> str:
    """Get the extension config file path"""
    return os.path.join(get_data_dir(), "extension_config.json")


def get_static_folder() -> str:
    """Get the static files directory path"""
    return os.path.join(get_data_dir(), "dist")
