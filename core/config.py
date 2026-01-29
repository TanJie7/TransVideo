
import json
import os
from PySide6.QtCore import QStandardPaths

class ConfigManager:
    def __init__(self):
        # Save to AppData/Local/TransNetV2/config.json
        self.config_dir = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), "TransNetV2")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.default_config = {
            "last_folder": "",
            "extract_keyframes": True,
            "skip_existing": True,
            "window_geometry": None
        }
        self.data = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            return self.default_config.copy()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self.default_config.copy()

    def save_config(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def get(self, key):
        return self.data.get(key, self.default_config.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save_config()
