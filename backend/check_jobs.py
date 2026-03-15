
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.job import Job
from app.core.config import settings

async def check_jobs():
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job).order_by(Job.created_at.desc()).limit(5))
        jobs = result.scalars().all()
        
        for job in jobs:
            print(f"ID: {job.id}")
            print(f"Status: {job.status}")
            print(f"Prompt: {job.prompt}")
            print(f"Error: {job.error}")
            print(f"Logs: {job.logs[:200]}...")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(check_jobs())
