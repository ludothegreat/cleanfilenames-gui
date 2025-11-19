from pathlib import Path
from config_manager import AppConfig, ConfigLoadError

try:
    AppConfig.load(Path("/tmp/non_existent_config.json"))
except FileNotFoundError as e:
    print(f"Successfully caught FileNotFoundError: {e}")
except ConfigLoadError as e:
    print(f"Caught ConfigLoadError: {e}")
except Exception as e:
    print(f"Caught unexpected exception: {e}")
