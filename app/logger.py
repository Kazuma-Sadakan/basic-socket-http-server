import os, logging
from utils import BASE_URL

LOG_FILE = os.path.join(BASE_URL, "test.log")
# open(LOG_FILE, mode="w").close()
logger = logging.getLogger("SERVER")
logger.setLevel(logging.INFO)
fh = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter("%(asctime)s: %(name)s: %(levelname)s: %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)