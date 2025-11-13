# tests/test_search.py
import asyncio
from modules.search import search_entries


async def test_search():
    results = await search_entries(team_id=1, filters={"q": "PLC"})
    assert len(results) > 0
    print("Tìm kiếm OK:", results[0])

if __name__ == "__main__":
    asyncio.run(test_search())
