import json
import os


CONFIG_PATH = "./data/config.json"


DEFAULT_CONFIG = {
    "default_model": "nvidia/nemotron-3-ultra:free",
    "models": {
        "orchestrator": "nvidia/nemotron-3-ultra:free",
        "planner": "nvidia/nemotron-3-ultra:free",
        "fixer": "nvidia/nemotron-3-ultra:free",
        "developer": "recursive/flint-v1.0:free",
        "qa": "nvidia/nemotron-3-ultra:free",
    },
    "providers": {},
    "review_policy": "balanced",
    "auto_review": True,
}


class ConfigManager:
    def __init__(self, path: str = CONFIG_PATH) -> None:
        self.path = path
        self.config: dict = json.loads(json.dumps(DEFAULT_CONFIG))
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    stored = json.load(f)
                self.config = {**json.loads(json.dumps(DEFAULT_CONFIG)), **stored}
            except (OSError, ValueError):
                self.config = json.loads(json.dumps(DEFAULT_CONFIG))
        else:
            self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.config, f, indent=2)

    def reload(self) -> None:
        self._load()

    def get_config(self) -> dict:
        return self.config

    def get_model(self, agent_name: str) -> str:
        models = self.config.get("models") or {}
        return models.get(agent_name) or self.config.get("default_model") or "nvidia/nemotron-3-ultra:free"

    def set_model(self, agent_name: str, model_id: str) -> None:
        self.config.setdefault("models", {})
        self.config["models"][agent_name] = model_id
        self._save()

    def get_providers(self) -> dict:
        return self.config.get("providers") or {}

    def add_provider(self, name: str, base_url: str, api_key: str) -> None:
        self.config.setdefault("providers", {})
        self.config["providers"][name] = {"base_url": base_url, "api_key": api_key}
        self._save()

    def delete_provider(self, name: str) -> None:
        providers = self.config.get("providers") or {}
        providers.pop(name, None)
        self.config["providers"] = providers
        self._save()

    def get_review_policy(self) -> str:
        return self.config.get("review_policy") or "balanced"

    def set_review_policy(self, policy: str) -> None:
        if policy not in ("strict", "balanced", "permissive"):
            raise ValueError(f"Invalid review policy: {policy}")
        self.config["review_policy"] = policy
        self._save()

    def get_auto_review(self) -> bool:
        return bool(self.config.get("auto_review", True))

    def set_auto_review(self, enabled: bool) -> None:
        self.config["auto_review"] = enabled
        self._save()


config_manager = ConfigManager()
