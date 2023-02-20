import glob
import json
import os
import shutil

import swifter

try:
    import GlobalData as GD
except ModuleNotFoundError:
    pass
import random

import networkx as nx
import pandas as pd
from PIL import Image

from . import settings as st
from .classes import LayoutAlgroithms
from .classes import LayoutTags as LT
from .classes import NodeTags as NT
from .classes import Organisms
from .settings import log


def get_algo_variables(algo: str, form: dict) -> dict:
    """Extract variables for an algorithm from the upload form.

    Args:
        algo (str): name of the algorithm. Possible names are given in settings.LayoutAlgroithms
        form (dict): dictionary containing all form elements.

    Returns:
        dict: dictionary of the needed variables for the picked algorithm.
    """
    if algo is None:
        return algo
    if "cg" in algo:
        return {
            "prplxty": form.get("string_cg_prplxty", 50),
            "density": form.get("string_cg_density", 12),
            "l_rate": form.get("string_cg_l_rate", 200),
            "steps": form.get("string_cg_steps", 250),
            "n_neighbors": form.get("string_cg_n_neighbors", 10),
            "spread": form.get("string_cg_spread", 1.0),
            "min_dist": form.get("string_cg_min_dist", 0.1),
        }
    if algo == LayoutAlgroithms.spring:
        opt_dist = form.get("string_spring_opt_dist", 0.0)
        if opt_dist == 0:
            opt_dist = None

        return {
            "opt_dist": opt_dist,
            "iterations": form.get("string_spring_iterations", 50),
            "threshold": form.get("string_spring_threshold", 0.0001),
        }
    else:
        return {}


def prepare_networkx_network(G: nx.Graph, positions: dict = None) -> tuple[dict, dict]:
    """Transforms a basic networkx graph into a correct data structure to be uploaded by the Cytoscape uploader. If the positions are not given, the positions are calculated using the spring layout algorithm of networkx.

    Args:
        G (nx.Graph): networkx graph to be transformed.
        positions (dict, optional): positions of the generated graph with node ids as keys and positions as values. Defaults to None.

    Returns:
        tuple[dict, dict]: First element contains the node data, second element contains the edge data.
    """
    if positions is None:
        positions = nx.spring_layout(G, dim=3)
    nodes_data = {}
    edges_data = {}
    for node in G.nodes():
        nodes_data[node] = {
            "pos": positions[node],
            "uniprotid": node,
            "display name": "Gene Name of the Protein",
        }
    for edge in G.edges():
        edges_data[edge] = {"source": edge[0], "target": edge[1]}
    return nodes_data, edges_data


def find_cy_layout(node: dict) -> tuple[dict, int]:
    """Find the index of the cytoscape layout in the layouts list of the node.

    Args:
        node (dict): node data

    Returns:
        tuple[dict, int]: first element is the layout data itself, second is the index of the layout.
    """
    cy_layout, idx = None, None
    if NT.layouts in node:
        for idx, layout in enumerate(node[NT.layouts]):
            if layout[LT.name] == LT.cy_layout:
                cy_layout = layout
                break
    return cy_layout, idx


def clean_filename(name: str) -> str:
    """Cleans the project name to be used in the file names.

    Args:
        name (str): String on which the cleaning should be performed.

    Returns:
        str: clean string
    """
    name = name.replace(" ", "_")
    name = name.replace("/", "_")
    name = name.replace("'", "")
    name = name.replace("´", "")
    name = name.replace("`", "")
    name = name.replace("'", "")
    name = name.replace("“", "")
    name = name.replace(",", "_")
    name = name.replace(".", "_")
    name = name.replace("-", "_")
    name = name.replace("–", "_")
    name = name.replace("#", "_")
    return name


def pepare_uploader() -> None:
    """Adds extension speciefic dta to the GD.sessionData."""
    strinEx_config = {}

    strinEx_config["layoutAlgos"] = LayoutAlgroithms.all_algos
    strinEx_config["actAlgo"] = LayoutAlgroithms.spring
    strinEx_config["organisms"] = Organisms.all_organisms

    GD.sessionData["stringex"] = strinEx_config


def move_on_boot() -> None:
    """Moves the projects directories of the interactomes to the projects directory of the VRNetzer backend."""
    for _dir in glob.glob(os.path.join(st._THIS_EXT_STATIC_PATH, "projects", "*")):
        dir_name = os.path.basename(_dir)
        if os.path.isdir(_dir) and not os.path.isdir(
            os.path.join(st._PROJECTS_PATH, dir_name)
        ):
            log.debug(f"Copying {_dir}")
            shutil.copytree(_dir, os.path.join(st._PROJECTS_PATH, dir_name))


if __name__ == "__main__":
    G = nx.Graph()
    G.add_edge("O15552", "Q76EI6")
    print(prepare_networkx_network(G))
