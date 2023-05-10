from config import config as cfg
import asyncpg

config = cfg["database"]

source_schema    = config["source_schema"]
marketing_schema = config["marketing_schema"]
users_schema     = config["users_schema"]

async def create_connection():
    conn = await asyncpg.connect(
        database=config["db_name"],
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"]
    )
    return conn
