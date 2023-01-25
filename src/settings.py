import os
from logging import DEBUG

from . import logger
from .classes import LayoutAlgroithms

_LOG_DEBUG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)s - %(funcName)s()] %(message)s"
_LOG_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_LOG_LEVEL = DEBUG

_LOG_FORMAT = _LOG_DEFAULT_FORMAT
F_LOG_LEVEL = _LOG_LEVEL
C_LOG_LEVEL = _LOG_LEVEL

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
MAX_NUM_LINKS = 264144
log = logger.get_logger(
    level=_LOG_LEVEL, f_level=F_LOG_LEVEL, c_level=C_LOG_LEVEL, format=_LOG_FORMAT
)


HELP_TEXT = (
    "Usage:\n"
    + "main.py query <query type=[protein/disease/compound/pubmed]> <query> <opt:cutoff> <opt:limit> <opt:species> <opt:taxonID>"
    + "\n"
    "or\n"
    + "main.py export <network> <filename> <opt:KeepTmp> <opt:*> <opt:overwrite_file>"
    + "\n"
    + "or\n"
    + "main.py project <network> <opt:layout_algo> <opt:keep_temp> <opt:skip_exists> <opt:project_name> <opt:gen_layout> <opt:cy_layout> <opt:stringify>"
    + "\n"
    + "or\n"
    + "main.py names"
    + "\n"
    + "or\n"
    + "main.py map <source_network> <target_network> <opt:output_name>"
    + "\n"
    + "or\n"
    + "main.py convert <node_list> <edge_list> <opt:uniprot_mapping> <opt:project_name>"
    + "\n"
    + "possible algorithms:\n"
    + ",".join(LayoutAlgroithms.all_algos)
)
