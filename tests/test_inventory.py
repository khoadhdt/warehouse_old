import asyncio
from modules.inventory import add_entry, get_connection, list_entries, get_current_stock, refresh_current_stock, delete_entry

TEAM_ID = 1
USER_ID = 1


async def test_inventory_flow():
    conn = await get_connection()
    try:
        info = await conn.fetchrow("SELECT current_database(), current_schema(), current_user;")
        print("KẾT NỐI TỪ PYTHON:")
        print(f"  Database: {info['current_database']}")
        print(f"  Schema:   {info['current_schema']}")
        print(f"  User:     {info['current_user']}")
    finally:
        await conn.close()

    print("🧱 Thêm giao dịch nhập kho ...")
    entry_id = await add_entry(
        component_id="099011",
        component_name="Module try",
        # tên này thuộc trong bảng "options" lọc cột "team_id" = team_id, "category"="groups" lấy giá trị cột "value" (chọn 1 trong list đó)
        group_name=["Setup Parts"],
        # tên này thuộc trong bảng "options" lọc cột "team_id" = team_id, "category"="process" lấy giá trị cột "value" (chọn một, vài cái trong list đó)
        process=["ACF", "Bending"],
        # tên này thuộc trong bảng "options" lọc cột "team_id" = team_id, "category"="model" lấy giá trị cột "value" (chọn 1 trong list đó)
        model=["AZ"],
        size="10x20x5",
        # tên này thuộc trong bảng "options" lọc cột "team_id" = team_id, "category"="unit" lấy giá trị cột "value" (chọn 1 trong list đó)
        unit="pcs",
        team_id=TEAM_ID,
        # tên này thuộc trong bảng "options" lọc cột "team_id" = team_id, "category"="material" lấy giá trị cột "value" (chọn một, vài cái trong list đó)
        material=["Metal"],
        # tên này thuộc trong bảng "options" lọc cột "team_id" = team_id, "category"="storage_location" lấy giá trị cột "value" (chọn 1 trong list đó)
        storage_location="Box 102",
        invoice="INV001",
        modinvoice="MOD001",
        # tên này thuộc trong bảng "options" lọc cột "team_id" = team_id, "category"="status" lấy giá trị cột "value" (chọn 1 trong list đó)
        status="Available",
        note="Nhập test",
        quantity=10,
        movement_type="in",
        created_by=USER_ID
    )
    print("✅ ID vừa tạo:", entry_id)

    print("📋 Danh sách giao dịch gần nhất:")
    rows = await list_entries(TEAM_ID)
    for r in rows[:3]:
        print(r)

    print("🔁 Làm mới view current_stock ...")
    await refresh_current_stock()

    print("📦 Kiểm tra tồn kho:")
    stock = await get_current_stock(TEAM_ID)
    for s in stock[:3]:
        print(s)

    print("🗑️ Xóa bản ghi test ...")
    # await delete_entry(entry_id, USER_ID)
    print("✅ Đã xóa thành công!")


if __name__ == "__main__":
    asyncio.run(test_inventory_flow())
