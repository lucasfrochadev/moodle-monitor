import sqlite3, os

path = os.path.join("data", "monitor.db")
conn = sqlite3.connect(path)
conn.row_factory = sqlite3.Row

# For each activity, find the most recent non-NULL due_date/open_date/cutoff_date
# across ALL its snapshots, and update broken snapshots
cur = conn.execute("""
    SELECT DISTINCT activity_id
    FROM activity_snapshots
    WHERE due_date IS NULL
""")
broken = [r["activity_id"] for r in cur.fetchall()]
print(f"Activities with broken (NULL due_date) snapshots: {len(broken)}")

fixed_due = 0
fixed_open = 0
fixed_cutoff = 0

for aid in broken:
    # Get the most recent non-NULL due_date
    cur = conn.execute("""
        SELECT due_date, open_date, cutoff_date
        FROM activity_snapshots
        WHERE activity_id = ?
          AND due_date IS NOT NULL
        ORDER BY version DESC
        LIMIT 1
    """, (aid,))
    best = cur.fetchone()
    if not best:
        continue

    # Update ALL snapshots for this activity that have NULL due_date
    cur = conn.execute("""
        UPDATE activity_snapshots
        SET due_date = ?
        WHERE activity_id = ? AND due_date IS NULL
    """, (best["due_date"], aid))
    fixed_due += cur.rowcount

    # Also fix open_date
    cur = conn.execute("""
        SELECT open_date FROM activity_snapshots
        WHERE activity_id = ? AND open_date IS NOT NULL
        ORDER BY version DESC LIMIT 1
    """, (aid,))
    best_open = cur.fetchone()
    if best_open and best_open["open_date"]:
        cur = conn.execute("""
            UPDATE activity_snapshots
            SET open_date = ?
            WHERE activity_id = ? AND open_date IS NULL
        """, (best_open["open_date"], aid))
        fixed_open += cur.rowcount

    # Also fix cutoff_date
    cur = conn.execute("""
        SELECT cutoff_date FROM activity_snapshots
        WHERE activity_id = ? AND cutoff_date IS NOT NULL
        ORDER BY version DESC LIMIT 1
    """, (aid,))
    best_cutoff = cur.fetchone()
    if best_cutoff and best_cutoff["cutoff_date"]:
        cur = conn.execute("""
            UPDATE activity_snapshots
            SET cutoff_date = ?
            WHERE activity_id = ? AND cutoff_date IS NULL
        """, (best_cutoff["cutoff_date"], aid))
        fixed_cutoff += cur.rowcount

conn.commit()
conn.close()
print(f"Fixed: due_date={fixed_due}, open_date={fixed_open}, cutoff_date={fixed_cutoff}")
