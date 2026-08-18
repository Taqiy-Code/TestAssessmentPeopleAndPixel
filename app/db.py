import asyncpg

async def create_pool() -> asyncpg.Pool:
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
    
    return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
 