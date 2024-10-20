DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 1030
DEFAULT_SYSTEM_PATH = ""

PATH = {
    "REQUIREMENTS": "/requirements_client.txt",
    "ENV": "/.env",
    "SETTINGS_UI": "/assets/qt/NetworkSettingsWidget.ui",
    "SMART_UI": "/assets/qt/SmartDataWidget.ui",
    "INFOUI": "/assets/qt/info.ui",
    "CANNOLOUI": "/assets/qt/cannolo_select.ui",
    "ICON": "/assets/icon.png",
    "VAPORWAVE_AUDIO": "/assets/vaporwave_theme.mp3",
    "ASD": "/assets/asd/asd.gif",
    "ASDVAP": "/assets/asd/asdvap.gif",
    "RELOAD": "/assets/reload/reload.png",
    "WHITERELOAD": "/assets/reload/reload_white.png",
    "VAPORWAVERELOAD": "/assets/reload/vapman.png",
    "PENDING": "/assets/table/pending.png",
    "PROGRESS": "/assets/table/progress.png",
    "OK": "/assets/table/ok.png",
    "WARNING": "/assets/table/warning.png",
    "ERROR": "/assets/table/error.png",
    "STOP": "/assets/stop.png",
    "WEEE": "/assets/backgrounds/weee_logo.png",
    "VAPORWAVEBG": "/assets/backgrounds/vaporwave.png",
    "SERVER": "/basilico.py",
    "THEMES": "/themes/",
}

URL = {
    "website": "https://weeeopen.polito.it",
    "source_code": "https://github.com/WEEE-Open/pesto",
}

IGNORE_SMART_RESULTS = [
    "json_format_version",
    "smartctl",
    "local_time",
]

QUEUE_TABLE = ["ID", "Process", "Disk", "Status", "Eta", "Progress"]

QUEUE_COMPLETED = "completed"
QUEUE_PROGRESS = "progress"
QUEUE_QUEUED = "queued"

LOCAL_MODE = "local"
REMOTE_MODE = "remote"

LATEST_SERVER_MODE = "latestServerMode"
LATEST_SERVER_IP = "latestServerIp"
LATEST_SERVER_PORT = "latestServerPort"
LATEST_DEFAULT_SYSTEM_PATH = "latestDefaultSystemPath"

QSETTINGS_IP_GROUP = "ipGroup"


PROGRESS_BAR_SCALE = 100

VERSION = "2.0.0"
