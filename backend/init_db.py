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
            
            # Create tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tables created successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(init_db())
