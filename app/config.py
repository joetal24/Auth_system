from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")

    APP_NAME : str = "Auth System"
    DEBUG : bool = False

    #database
    DATABASE_URL : str
    
    #Redis
    REDIS_URL:str = "redis://localhost:6379/0"

    #JWT
    SECRET_KEY: str
    ALGORITHM:str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    #CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8000"]


#Fill this in yourself:
settings = Settings() # reads from .env automatically
