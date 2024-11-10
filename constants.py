# PINOLO

LOCAL_IP = "127.0.0.1"
DEFAULT_PORT = 1030
LOCAL_IMAGES_DIRECTORY = "localImagesDirectory"
LOCAL_DEFAULT_IMAGE = "localDefaultImage"

CLIENT_TIMEOUT = 5

PATH = {
    "REQUIREMENTS": "/requirements.txt",
    "ENV": "/.env",
    "SETTINGS_UI": "/assets/qt/NetworkSettingsDialog.ui",
    "SMART_UI": "/assets/qt/SmartDataDialog.ui",
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

DRIVES_TABLE_NAME = 0
DRIVES_TABLE_STATUS = 1
DRIVES_TABLE_TARALLO_ID = 2
DRIVES_TABLE_DRIVE_SIZE = 3

QUEUE_TABLE = ["ID", "Process", "Disk", "Status", "Eta", "Progress"]

QUEUE_TABLE_DRIVE = 0
QUEUE_TABLE_PROCESS = 1
QUEUE_TABLE_STATUS = 2
QUEUE_TABLE_ETA = 3
QUEUE_TABLE_PROGRESS = 4

QUEUE_LABELS = {
    "queued_badblocks": "Erase",
    "queued_smartctl": "Smart Check",
    "smartctl": "Smart Check",
    "queued_cannolo": "Load System",
    "queued_sleep": "HDD Stop",
    "queued_upload_to_tarallo": "Upload Data",
}

QUEUE_COMPLETED = "completed"
QUEUE_PROGRESS = "progress"
QUEUE_QUEUED = "queued"

LOCAL_MODE = "Local"
REMOTE_MODE = "Remote"

CURRENT_SERVER_MODE = "serverMode"
CURRENT_SERVER_IMAGES_DIRECTORY = "ImagesDirectory"
CURRENT_SERVER_DEFAULT_IMAGE = "defaultImage"
CURRENT_SERVER_CONFIG_KEY = "serverConfig"

QSETTINGS_IP_GROUP = "ipGroup"

PROGRESS_BAR_SCALE = 100

# BASILICO

# TODO

# GENERIC
VERSION = "2.0.0"
