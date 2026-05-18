import sqlite3
s = sqlite3.connect("data/study.db")

# Check all boards
boards = s.execute("SELECT id, name FROM boards").fetchall()
print("Boards:")
for b in boards:
    cols = s.execute("SELECT id, name FROM columns WHERE board_id = ? ORDER BY position", (b[0],)).fetchall()
    print(f"  {b[1]} ({b[0][:8]}...): {len(cols)} columns")
    for c in cols:
        tasks = s.execute("SELECT title, due_date, status FROM tasks WHERE column_id = ? AND archived = 0", (c[0],)).fetchall()
        print(f"    {c[1]}: {len(tasks)} tasks")
        for t in tasks[:3]:
            print(f"      - {t[0][:40]:40s} due={t[1]} {t[2]}")
        if len(tasks) > 3:
            print(f"      ... and {len(tasks)-3} more")

print()
# Check how many have due >= today
for b in boards:
    n = s.execute("""
        SELECT COUNT(*) FROM tasks WHERE board_id = ? AND archived = 0 
        AND due_date IS NOT NULL AND due_date >= DATE('now')
    """, (b[0],)).fetchone()[0]
    total = s.execute("SELECT COUNT(*) FROM tasks WHERE board_id = ? AND archived = 0", (b[0],)).fetchone()[0]
    print(f"{b[1]}: {n}/{total} tasks with due >= today")

s.close()
