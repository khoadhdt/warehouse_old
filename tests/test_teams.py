import asyncio
from modules.teams import list_teams, get_team_by_name, create_team


async def test_team_flow():
    print("📋 Danh sách team hiện tại:")
    teams = await list_teams()
    for t in teams:
        print(t)

    print("➕ Thêm team EOL ...")
    await create_team("EOL", "Nhóm EOL", "D:\Backup data all\Managementdata\Other\inventory_management_images_EOL", "\\172.23.10.230\map-eng\8. BAO CAO THIET BI EOL\6. Data quan trong\22.Xac nhan Invoice\EOL INV")

    print("🔍 Kiểm tra team EOL ...")
    team = await get_team_by_name("EOL")
    print(team)


if __name__ == "__main__":
    asyncio.run(test_team_flow())
