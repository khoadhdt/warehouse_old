# tests/test_auth.py
import asyncio
from modules.auth import create_user, verify_user


async def test_auth_flow():
    print("🧱 Tạo user test: admin / 123456 ...")
    await create_user("admin", "123456", role="admin", team_id=1)

    print("🔐 Kiểm tra đăng nhập ...")
    user = await verify_user("admin", "123456")
    if user:
        print("✅ Đăng nhập thành công:", user)
    else:
        print("❌ Sai thông tin đăng nhập!")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())
