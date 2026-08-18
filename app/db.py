import asyncpg

async def create_pool() -> asyncpg.Pool:
    DATABASE_URL = "postgresql://root:root@127.0.0.1:5433/pnp_db"

    return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
 