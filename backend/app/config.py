from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolves to `backend/.env` regardless of where uvicorn is launched from
_ENV_FILE = Path(__file__).parent.parent / ".env"

class Settings(BaseSettings):
    
    # Sets up the needed information to access the .env file secret configs
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
    )

    # The secrets that will are in the .env file
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

settings = Settings() # This is loaded from the .env file