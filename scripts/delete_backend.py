"""
Delete the BACKEND PHP activity (B2 - Site com BACKEND em PHP) from both databases.
Use this before testing Sincronizar to verify the scraper + sync flow.
"""
import sqlite3, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTIVITY_ID = "8858a4f9-0280-59f3-b55b-e41b2d9ad710"

# --- Monitor DB ---
path = os.path.join(BASE, "data", "monitor.db")
conn = sqlite3.connect(path)

r = conn.execute("SELECT name FROM activities WHERE id = ?", (ACTIVITY_ID,)).fetchone()
if not r:
    print("[monitor.db] Activity not found (already deleted).")
else:
    print(f"[monitor.db] Deleting: {r[0]}")
    conn.execute("DELETE FROM activity_files WHERE activity_id = ?", (ACTIVITY_ID,))
    conn.execute("DELETE FROM activity_snapshots WHERE activity_id = ?", (ACTIVITY_ID,))
    conn.execute("DELETE FROM detected_changes WHERE activity_id = ?", (ACTIVITY_ID,))
    conn.execute("DELETE FROM activities WHERE id = ?", (ACTIVITY_ID,))
    conn.commit()
    print("  Done.")
conn.close()

# --- Study DB ---
path2 = os.path.join(BASE, "data", "study.db")
conn2 = sqlite3.connect(path2)

cur = conn2.execute(
    """SELECT ai.id, ai.task_id, t.title
       FROM activity_imports ai
       LEFT JOIN tasks t ON t.id = ai.task_id
       WHERE ai.source_activity_id = ?""",
    (ACTIVITY_ID,),
)
for r in cur.fetchall():
    print(f"[study.db] Deleting: {r[2]} ({r[1]})")
    conn2.execute("DELETE FROM task_history WHERE task_id = ?", (r[1],))
    conn2.execute("DELETE FROM notifications WHERE task_id = ?", (r[1],))
    conn2.execute("DELETE FROM activity_imports WHERE id = ?", (r[0],))
    conn2.execute("DELETE FROM tasks WHERE id = ?", (r[1],))
    conn2.commit()
    print("  Done.")

cur2 = conn2.execute("SELECT id, title FROM tasks WHERE title LIKE '%BACKEND%'")
for r in cur2.fetchall():
    print(f"[study.db] Deleting orphan: {r[1]} ({r[0]})")
    conn2.execute("DELETE FROM task_history WHERE task_id = ?", (r[0],))
    conn2.execute("DELETE FROM notifications WHERE task_id = ?", (r[0],))
    conn2.execute("DELETE FROM activity_imports WHERE task_id = ?", (r[0],))
    conn2.execute("DELETE FROM tasks WHERE id = ?", (r[0],))
    conn2.commit()
    print("  Done.")

conn2.close()
print("\nReady. Click Sincronizar to test.")
