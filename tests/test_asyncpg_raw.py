import asyncio
import asyncpg


async def main():
    print("Kết nối asyncpg trực tiếp (ssl=False)...")
    conn = await asyncpg.connect(
        host="172.23.8.153",
        port=5432,
        user="postgres",
        password="wsepc",
        database="warehouse_db",
        ssl=False  # 🚀 Không dùng SSL
    )
    ver = await conn.fetchval("SELECT version()")
    print("✅ Kết nối thành công:", ver)
    await conn.close()

asyncio.run(main())
