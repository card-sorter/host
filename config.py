from pyprojroot import here
import os

RPC_HOST = "localhost"
RPC_PORT = 8080
BAUD_RATE = 115200
SERIAL_PORT = "/dev/ttyACM0"
GRBL_CONNECTION = b"Grbl 1.1h ['$' for help]\r\n"
BIN_POSITIONS = [(14, 0), (90, 0), (166, 0), (243, 0), (319, 0)]
BIN_HEIGHT = -30
BIN_BOTTOM_LIMIT = -105
MOVEMENT_HEIGHT = 0
CAMERA_HEIGHT = -25
PROBE_SAFETY_DISTANCE = 4
PROBE_FEEDRATE = 500
CARD_DROP_OFFSET = 15
CARD_LIFT_DELAY = 1
PROJ_ROOT = here()
DATABASE = {
    "path": os.path.join(PROJ_ROOT, "db/database.db"),
}
CAMERA_BIN = 0
TASKS = [
    {
        "name":"Scan Cards",
        "module":"scan",
        "description":"Scan cards and add to database"
    },
    {
        "name":"Scan Barcodes",
        "module":"scan_barcodes",
        "description":"Scan barcodes and add to database"
    },
    {
        "name":"Sort Cards",
        "module":"sort",
        "description":"Sort already scanned cards"
    }
]