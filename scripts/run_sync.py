import sys, os, json

sys.path.insert(0, os.path.abspath("."))
from api.database import db
from api.services.sync_service import SyncService

db.connect()
monitor_path = os.path.join(os.path.abspath("."), "data", "monitor.db")
svc = SyncService(monitor_db_path=monitor_path)
result = svc.sync()
print(json.dumps({k: str(v) for k, v in result.items()}, indent=2, ensure_ascii=False))
