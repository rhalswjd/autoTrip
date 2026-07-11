from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AutoTrip API"
    environment: str = "local"
    debug: bool = False
    log_level: str = "INFO"
    
    backend_cors_origins: list[str] = ["http://localhost:5173"]
    
    notion_api_key: str = ""
    notion_database_id: str = ""
    
    scraper_base_url: str = "https://www.jr-odekake.net/railroad/eki/"
    
    sqlite_cache_path: str = "autotrip_cache.db"
    sqlite_station_db_path: str = "autotrip_stations.db"
    
    cache_ttl_seconds: int = 3600
    
    request_timeout: int = 10
    request_retry: int = 3
    request_delay: float = 1.0
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
