import sqlite3
s = sqlite3.connect("data/study.db")

pairs = [
    "FRONT-END EM REACT",
    "BACKEND em PHP",
    "Projeto - Final",
    "Controle Financeiro",
]
for p in pairs:
    r = s.execute("""
        SELECT t.title, t.due_date, t.status
        FROM tasks t
        JOIN activity_imports ai ON ai.task_id = t.id
        WHERE t.title LIKE ?
    """, (f"%{p[:15]}%",)).fetchone()
    if r:
        due = r[1] or "None"
        vig = "YES" if due != "None" and due >= "2026-05-17" else "NO (vencido/passado)"
        print(f"{p:30s} | due={due:25s} | {r[2]:10s} | vigentes? {vig}")
    else:
        print(f"{p:30s} | NOT FOUND")

# Count vigentes
n = s.execute("""
    SELECT COUNT(*) FROM tasks t
    JOIN boards b ON b.id = t.board_id
    WHERE b.name = 'Atividades Vigentes'
    AND t.due_date IS NOT NULL
    AND t.due_date >= DATE('now')
    AND t.archived = 0
""").fetchone()[0]
print(f"\nTotal vigentes agora: {n}")

s.close()
