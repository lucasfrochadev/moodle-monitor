import sys, asyncio, logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
from src.config.settings import Config
from src.monitor.engine import MonitorEngine
cfg = Config()
cfg.monitoring.course_ids = [15659]
engine = MonitorEngine(cfg)
asyncio.run(engine.once())
