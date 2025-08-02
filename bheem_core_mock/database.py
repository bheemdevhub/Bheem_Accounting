"""Mock database module for production deployment"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Create the base class for models
Base = declarative_base()

# Mock database session functions
def get_database_url():
    """Get database URL from environment variables"""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "bheem_accounting")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "password123")
    
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"

def create_async_database_engine():
    """Create async database engine"""
    database_url = get_database_url()
    return create_async_engine(database_url, echo=False)

def create_async_session_factory():
    """Create async session factory"""
    engine = create_async_database_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Create global session factory
async_session_factory = create_async_session_factory()

async def get_async_session():
    """Get async database session"""
    async with async_session_factory() as session:
        yield session
