#!python3
import json
import os
import sys
from argparse import ArgumentParser

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src import settings as st

st._WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
st._STATIC_PATH = os.path.join(st._WORKING_DIR, "static")
st._PROJECTS_PATH = os.path.join(st._STATIC_PATH, "projects")
st._NETWORKS_PATH = os.path.join(st._STATIC_PATH, "networks")

# _STYLES_PATH = os.path.join(_STATIC_PATH, "styles")
os.makedirs(st._PROJECTS_PATH, exist_ok=os.X_OK)
os.makedirs(st._NETWORKS_PATH, exist_ok=os.X_OK)
# os.makedirs(_STYLES_PATH, exist_ok=os.X_OK)

from src import workflows as wf


def upload_from_VRNetz(
    vrnetz_file: str,
    project_name: str,
    algo: str,
    tags: dict = None,
    cg_variables: dict = None,
) -> str:
    """Used to uplaod VRNetzer files to the VRNetzer

    Args:
        network (json): Loaded network (loaded with json.load)
        filename (str): Name of the network file which is uploaded
        project_name (str): Name of the project to be created.
        tags (dict,optional): Dictionary of tags to options in underlying functions. Defaults to None.
        cg_variables (dict, optional): dictionary containing varaibles for cartoGRAPHs variables. Defaults to None.

    Returns:
        str: HTML string to reflect whether the upload was successful or not.
    """
    with open(vrnetz_file, "r") as f:
        network = json.load(f)
    # wf.VRNetzer_upload_workflow(
    #     network, vrnetz_file, project_name, algo, tags, cg_variables
    # )


def main():
    """Main function will take the arguments passed by the user and execute the program accordingly."""
    parser = ArgumentParser(prog=__file__)
    subparsers = parser.add_subparsers(help="mode", dest="mode")
    upload_parser = subparsers.add_parser(
        "upload", help="Upload a network in VRNetz format to the VRNetzer."
    )
    parser.add_argument(
        "-network",
        "--n",
        type=str,
        help="Defines, the file to upload.",
    )
    parser.add_argument(
        "-project",
        "--p",
        type=str,
        help="Defines the name of the project.",
    )
    parser.add_argument(
        "-algo",
        "--a",
        nargs="?",
        type=str,
        help="Defines the layout algorithm to be used.",
    )
    if parser.parse_args().mode == None:
        parser.parse_args(["-h"])
        exit()
    if parser.parse_args().mode == "upload":
        upload_from_VRNetz(
            parser.parse_args().n,
            parser.parse_args().p,
            parser.parse_args().a,
        )


if __name__ == "__main__":
    main()
