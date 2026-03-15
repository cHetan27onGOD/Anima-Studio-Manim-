import asyncio
import logging
from sqlalchemy import text
from app.db.session import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_db():
    logger.info("Updating database schema...")
    try:
        async with engine.begin() as conn:
            # Add progress column to jobs table if it doesn't exist
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS progress JSONB"))
            logger.info("Schema updated successfully (progress column added).")
    except Exception as e:
        logger.error(f"Database update failed: {e}")

if __name__ == "__main__":
    asyncio.run(update_db())
