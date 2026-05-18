import sqlite3
m = sqlite3.connect("data/monitor.db")

# Check BACKEND snapshots
r = m.execute("""
    SELECT a.name, sn.version, sn.due_date, sn.taken_at
    FROM activity_snapshots sn
    JOIN activities a ON a.id = sn.activity_id
    WHERE a.name LIKE '%BACKEND%'
    ORDER BY sn.version DESC LIMIT 2
""").fetchall()
print("BACKEND snapshots:")
for row in r:
    print(f"  v{row[1]}: due={row[2]}, taken={row[3]}")

# Also check if maybe the snapshot was overwritten by a newer scrape
r2 = m.execute("""
    SELECT COUNT(*) FROM activity_snapshots sn
    JOIN activities a ON a.id = sn.activity_id
    WHERE a.name LIKE '%BACKEND%'
""").fetchone()
print(f"Total snapshots for BACKEND: {r2[0]}")

m.close()
