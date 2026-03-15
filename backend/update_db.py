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
            # Ensure users table exists (if init_db failed or skipped)
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
            
            # Add progress column to jobs table if it doesn't exist
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS progress JSONB"))
            
            # Add owner_id to jobs table if it doesn't exist
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS owner_id UUID"))
            
            # Add foreign key if not already present
            try:
                await conn.execute(text("ALTER TABLE jobs ADD CONSTRAINT fk_jobs_owner FOREIGN KEY (owner_id) REFERENCES users (id)"))
            except:
                pass # Already exists or table not ready
            
            logger.info("Schema updated successfully.")
    except Exception as e:
        logger.error(f"Database update failed: {e}")

if __name__ == "__main__":
    asyncio.run(update_db())
