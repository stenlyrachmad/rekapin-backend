from loguru import logger
import sys
from app.config import settings

logger.remove()
logger.add(sys.stdout, level=settings.__dict__.get("LOG_LEVEL", "INFO"))
