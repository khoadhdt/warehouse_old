
import asyncio
from sqlalchemy import text
from db.database import engine


async def test_connect():
    async with engine.begin() as conn:
        print(engine.url)  # in ra connection string để kiểm tra
        result = await conn.execute(text("SELECT version()"))
        row = result.first()  # ✅ lấy dòng đầu tiên (không cần await)
        print("✅ Kết nối PostgreSQL thành công:")
        print(row[0])         # ✅ in nội dung phiên bản PostgreSQL

asyncio.run(test_connect())
