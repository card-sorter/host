from pyprojroot import here
import os
from libcamera import controls

RPC_HOST = "localhost"
RPC_PORT = 8080
BAUD_RATE = 115200
SERIAL_PORT = "/dev/ttyACM0"
GRBL_CONNECTION = b"Grbl 1.1h ['$' for help]\r\n"
BIN_POSITIONS = [(14, 0), (91, 0), (167, 0), (244, 0), (320, 0)]
BIN_HEIGHT = -30
BIN_BOTTOM_LIMIT = -105
MOVEMENT_HEIGHT = 0
CAMERA_HEIGHT = -25
CAMERA_CONFIG = {
    #'ExposureTime': 66645, 
    #'AnalogueGain': 7.757575988769531, 
    #'ColourGains': (1.4118220806121826, 3.3094003200531006)
    "AfMode": controls.AfModeEnum.Manual, 
    "LensPosition": 1/0.052,
    }
PROBE_SAFETY_DISTANCE = 5
PROBE_FEEDRATE = 500
CARD_DROP_OFFSET = 15
CARD_LIFT_DELAY = 1
PROJ_ROOT = here()
DATABASE = {
    "path": os.path.join(PROJ_ROOT, "db/database.db"),
}
CAMERA_BIN = 0
WARP_INFO = ((4608//2,2592//2), 90, 1.25)
DEFAULT_TASK = "Sort Cards"