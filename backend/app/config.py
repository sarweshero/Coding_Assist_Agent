from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables / .env file."""

    # LLM provider keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # Model routing per agent (LiteLLM format, e.g. openrouter/<vendor>/<model>)
    DEFAULT_MODEL: str = "nvidia/nemotron-3-ultra:free"
    AGENT_MODELS: dict = {
        # Reasoning / planning / requirement analysis / bug fixes
        "orchestrator": "nvidia/nemotron-3-ultra:free",
        "planner": "nvidia/nemotron-3-ultra:free",
        "fixer": "nvidia/nemotron-3-ultra:free",
        # Code writing and editing
        "developer": "recursive/flint-v1.0:free",
        # Test generation / QA reasoning
        "qa": "nvidia/nemotron-3-ultra:free",
    }

    SQLITE_PATH: str = "./data/conding_assist.db"
    LOCAL_WORKSPACE_ROOT: str = "./data/workspace"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
