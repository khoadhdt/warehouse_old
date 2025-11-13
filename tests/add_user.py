# tests/reset_admin_user.py
import asyncio
from modules.auth import get_connection, create_user


async def reset_admin():
    conn = await get_connection()
    try:
        print("🧹 Xóa user 'admin' nếu tồn tại...")
        await conn.execute("DELETE FROM users WHERE username = $1", "admin")
        print("✅ Đã xóa xong!")

    finally:
        await conn.close()

    print("🧱 Tạo lại user admin / 123456 ...")
    await create_user("admin", "123456", role="admin", team="WSE")
    print("✅ Tạo mới thành công!")

if __name__ == "__main__":
    asyncio.run(reset_admin())
