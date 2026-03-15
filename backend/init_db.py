import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine
from app.db.base import Base
from app.models.job import Job
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    logger.info("Initializing database...")
    try:
        async with engine.begin() as conn:
            # Check if we can connect
            await conn.execute(text("SELECT 1"))
            logger.info("Connection successful.")
            
            # Create tables if they don't exist
            # Note: metadata.create_all is safe to call multiple times
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tables created or verified successfully.")
            
            # Specifically ensure the users table exists with correct columns
            # (as metadata.create_all might skip if partial tables exist)
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY,
                    email VARCHAR UNIQUE NOT NULL,
                    hashed_password VARCHAR NOT NULL,
                    full_name VARCHAR,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            logger.info("Users table verified.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(init_db())
