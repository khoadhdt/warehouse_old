# tests.test_asyncpg_ssl.py
import asyncio
import asyncpg
import ssl


async def main():
    print("Thử kết nối asyncpg qua SSL context ...")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        host="172.23.8.153",
        port=5432,
        user="postgres",
        password="wsepc",
        database="warehouse_db",
        ssl=ssl_context,   # 🔥 Dùng SSL context
        timeout=15
    )

    ver = await conn.fetchval("SELECT version()")
    print("✅ Kết nối thành công:", ver)
    await conn.close()

asyncio.run(main())
