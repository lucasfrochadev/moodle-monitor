import sqlite3, os

conn = sqlite3.connect(os.path.join("data", "monitor.db"))

for name, correct_date in [
    ("Projeto - Final", "2026-05-22 22:45:00"),
    ("Controle Financeiro", "2026-05-20 00:00:00"),
]:
    cur = conn.execute("""
        SELECT COUNT(*) FROM activity_snapshots s
        JOIN activities a ON a.id = s.activity_id
        WHERE a.name = ?
    """, (name,))
    count = cur.fetchone()[0]
    print(f"{name}: {count} snapshots")

    conn.execute("""
        UPDATE activity_snapshots
        SET due_date = ?
        WHERE id IN (
            SELECT s.id FROM activity_snapshots s
            JOIN activities a ON a.id = s.activity_id
            WHERE a.name = ?
        )
    """, (correct_date, name))
    conn.commit()
    print(f"  -> fixed to {correct_date}")

    cur = conn.execute("""
        SELECT s.due_date, s.version
        FROM activity_snapshots s
        JOIN activities a ON a.id = s.activity_id
        WHERE a.name = ?
        ORDER BY s.version DESC LIMIT 3
    """, (name,))
    for r in cur.fetchall():
        print(f"  v={r[1]} due={r[0]}")

conn.close()
