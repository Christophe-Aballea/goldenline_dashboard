from config import config as cfg
import asyncpg

config = cfg["database"]

async def create_connection():
    conn = await asyncpg.connect(
        database=config["db_name"],
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"]
    )
    return conn
