# tests/test_options.py
import asyncio
from modules.options import upsert_options, get_options, get_all_categories, clear_team_options

TEAM_ID = 1
CREATE_BY = 1


async def test_options_flow():
    print("🧹 Xóa dữ liệu cũ...")
    await clear_team_options(TEAM_ID)

    print("🧱 Tạo danh sách 'try' ...")
    await upsert_options(TEAM_ID, "try", ["Cái", "Lít", "Kg", "Thùng"], created_by=CREATE_BY)

    print("🧱 Tạo danh sách 'category_product' ...")
    await upsert_options(TEAM_ID, "category_product", ["Điện", "Cơ khí", "Hóa chất"], created_by=CREATE_BY)

    print("🔍 Kiểm tra danh sách 'try' ...")
    rows = await get_options(TEAM_ID, "try")
    for r in rows:
        print(r)

    print("📦 Lấy tất cả danh mục ...")
    all_cats = await get_all_categories(TEAM_ID)
    for k, v in all_cats.items():
        print(f"{k}: {v}")

    print("✅ Test hoàn tất!")

if __name__ == "__main__":
    asyncio.run(test_options_flow())
