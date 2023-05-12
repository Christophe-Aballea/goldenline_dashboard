from config import get_connection_db
import asyncpg


async def create_connection():
    host, port, user, password, db_name = get_connection_db()
    conn = await asyncpg.connect(database=db_name, host=host, port=port, user=user, password=password)
    return conn
