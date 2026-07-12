import os
from backend.core.config import settings
from backend.main import __file__ as main_file

print("Repository Default:", settings.sqlite_station_db_path)
print("Startup DB Path:", os.path.join(os.path.dirname(main_file), "autotrip_stations.db"))
