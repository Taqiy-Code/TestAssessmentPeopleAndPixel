import asyncpg
import os

from dotenv import load_dotenv
load_dotenv()

async def create_pool() -> asyncpg.Pool:

    return await asyncpg.create_pool(os.getenv("DATABASE_URL", ""), min_size=1, max_size=10)
 