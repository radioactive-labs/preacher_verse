import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    def __init__(self):
        self._load_yaml_config()
        self._load_env_config()

    def _load_yaml_config(self):
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        with open(config_path, 'r') as f:
            self.yaml_config = yaml.safe_load(f)

    def _load_env_config(self):
        # API Keys (required)
        self.DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

        # Server Configuration
        self.WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
        self.WS_PORT = int(os.getenv("WS_PORT", "8765"))
        self.HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
        self.HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))

        # Application Settings
        self.COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "30"))
        self.RANKING_CONFIDENCE_THRESHOLD = int(os.getenv("RANKING_CONFIDENCE_THRESHOLD", "75"))
        self.CONTEXT_WINDOW_SECONDS = int(os.getenv("CONTEXT_WINDOW_SECONDS", "60"))
        self.ACTIVE_WINDOW_SECONDS = int(os.getenv("ACTIVE_WINDOW_SECONDS", "10"))

    def get(self, key: str, default=None):
        """Get config value from YAML config."""
        keys = key.split('.')
        value = self.yaml_config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


config = Config()
