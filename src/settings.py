import os
from logging import DEBUG, INFO

from . import logger
from .classes import LayoutAlgorithms

_LOG_DEBUG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)s - %(funcName)s()] %(message)s"
_LOG_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_LOG_LEVEL = DEBUG

_LOG_FORMAT = _LOG_DEFAULT_FORMAT
F_LOG_LEVEL = _LOG_LEVEL
C_LOG_LEVEL = INFO

_WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
_THIS_EXT = os.path.join(_WORKING_DIR, "..")
_EXTENSION_PATH = os.path.join(_WORKING_DIR, "..", "..")
_VRNETZER_PATH = os.path.join(_EXTENSION_PATH, "..")

_STATIC_PATH = os.path.join(_VRNETZER_PATH, "static")  # Static path of the VRNetzer
_PROJECTS_PATH = os.path.join(_STATIC_PATH, "projects")
_NETWORKS_PATH = os.path.join(_STATIC_PATH, "networks")

_THIS_EXT_TEMPLATE_PATH = os.path.join(
    _WORKING_DIR, "..", "templates"
)  # Template path of this extension
_THIS_EXT_STATIC_PATH = os.path.join(
    _WORKING_DIR, "..", "static"
)  # Static path of this extension
_VRNETZER_PATH = os.path.join(_WORKING_DIR, "..", "..")
_VRNETZER_TEMPLATE_PATH = os.path.join(_VRNETZER_PATH, "templates")
# _STYLES_PATH = os.path.join(_STATIC_PATH, "styles")
os.makedirs(_PROJECTS_PATH, exist_ok=os.X_OK)
os.makedirs(_NETWORKS_PATH, exist_ok=os.X_OK)
# os.makedirs(_STYLES_PATH, exist_ok=os.X_OK)

UNIPROT_MAP = os.path.join(_STATIC_PATH, "uniprot_mapping.csv")
_MAPPING_ARBITARY_COLOR = [255, 255, 255]
MAX_NUM_LINKS = 262144
log = logger.get_logger(
    level=_LOG_LEVEL,
    f_level=F_LOG_LEVEL,
    c_level=C_LOG_LEVEL,
    format=_LOG_FORMAT,
    c_format=_LOG_FORMAT,
)
