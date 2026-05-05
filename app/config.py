from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    
    # Database
    postgres_host: str 
    postgres_port: int 
    postgres_db: str 
    postgres_user: str 
    postgres_password: str 


    # Database - Chat Memory (chatAi)
    chat_db_host: str 
    chat_db_port: int 
    chat_db_name: str 
    chat_db_user: str 
    chat_db_password: str 
    
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8005
    debug: bool = True
    
    # Supabase
    supabase_url: str
    supabase_key: str
    
    # MCP
    mcp_server_url: str
    mcp_timeout: int = 60000
     
    @property
    def database_url(self) -> str:
        """URL for main database (vmbe) - used by MCP tools"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def async_database_url(self) -> str:
        """Async URL for main database (vmbe)"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def chat_database_url(self) -> str:
        """URL for chat memory database (chatAi)"""
        return f"postgresql://{self.chat_db_user}:{self.chat_db_password}@{self.chat_db_host}:{self.chat_db_port}/{self.chat_db_name}"
    
    @property
    def async_chat_database_url(self) -> str:
        """Async URL for chat memory database (chatAi)"""
        return f"postgresql+asyncpg://{self.chat_db_user}:{self.chat_db_password}@{self.chat_db_host}:{self.chat_db_port}/{self.chat_db_name}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()