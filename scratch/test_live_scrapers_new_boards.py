import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scrapers.board_registry import get_board_runner

new_boards = [
    ("PyJobs", "Python"),
    ("UIUXJobsBoard", "Designer"),
    ("DjangoProject", "Python"),
    ("RemotePython", "Python"),
    ("4DayWeek", "Engineer"),
    ("RemoteGameJobs", "Animator"),
    ("HeyMarketers", "Marketing"),
    ("Twine", "Marketing"),
    ("BerlinStartupJobs", "Engineer"),
    ("PythonJobsGithub", "Python"),
    ("Nodesk", "AI"),
    ("Hasjob", "AI"),
]

async def main():
    print("Testing all 12 newly integrated boards via Board Registry runners...\n")
    passed = 0
    total = len(new_boards)
    for board_name, keyword in new_boards:
        runner = get_board_runner(board_name)
        if not runner:
            print(f"FAILED: No runner found for {board_name}")
            continue
        try:
            jobs = await runner(keyword=keyword, location="Remote", limit=5)
            print(f"SUCCESS: {board_name:20} -> {len(jobs)} jobs extracted for '{keyword}'")
            if jobs:
                print(f"         Sample: [{jobs[0].get('title')}] at [{jobs[0].get('company')}] ({jobs[0].get('listing_url')[:60]}...)")
            passed += 1
        except Exception as e:
            print(f"ERROR:   {board_name:20} -> {e}")

    print(f"\nResult: {passed}/{total} runners passed successfully.")

if __name__ == "__main__":
    asyncio.run(main())

