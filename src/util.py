import glob
import logging
import os
import shutil
import json

try:
    import GlobalData as GD
except ModuleNotFoundError:
    pass
import networkx as nx
from PIL import Image

from . import settings as st
from .classes import LayoutAlgroithms
from .classes import LayoutTags as LT
from .classes import NodeTags as NT
from .classes import Organisms
from .settings import log
import pandas as pd
import random


def get_algo_variables(algo: str, form: dict) -> dict:
    """Extract variables for an algorithm from the upload form.

    Args:
        algo (str): name of the algorithm. Possible names are given in settings.LayoutAlgroithms
        form (dict): dictionary containing all form elements.

    Returns:
        dict: dictionary of the needed variables for the picked algorithm.
    """
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


def extract_node_data(selected_nodes: list[int], project: str, layout: str, color: str):
    project_path = os.path.join(st._PROJECTS_PATH, project)
    with open(os.path.join(project_path, "nodes.json"), "r") as f:
        nodes_data = pd.DataFrame(json.load(f)["nodes"])
        if not selected_nodes:
            n = len(nodes_data)
            if n > 2000:
                n = 2000
            selected_nodes = random.sample(range(len(nodes_data)), n)
        nodes_data = nodes_data[nodes_data["id"].isin(selected_nodes)]
    if "layouts" in nodes_data.columns:
        nodes_data = nodes_data.drop(columns=["layouts"])
    if "display name" in nodes_data.columns:
        nodes_data["name"] = nodes_data["display name"]
        nodes_data = nodes_data.drop(columns=["display name", NT.name])

    with open(os.path.join(project_path, "pfile.json"), "r") as f:
        pfile = json.load(f)

    if layout not in pfile["layouts"]:
        layout = pfile["layouts"][0]

    if color not in pfile["layoutsRGB"]:
        color = pfile["layoutsRGB"][0]

    node_pos_l = list(
        Image.open(os.path.join(project_path, "layouts", layout + ".bmp")).getdata()
    )

    node_pos_h = list(
        Image.open(os.path.join(project_path, "layoutsl", layout + "l.bmp")).getdata()
    )

    node_colors = list(
        Image.open(os.path.join(project_path, "layoutsRGB", color + ".png")).getdata()
    )

    node_colors = [node_colors[c] for c in selected_nodes]
    node_pos_l = [node_pos_l[c] for c in selected_nodes]
    node_pos_h = [node_pos_h[c] for c in selected_nodes]

    def rgb_to_hex(r, g, b):
        return "#{:02x}{:02x}{:02x}".format(r, g, b)

    nodes_data["color"] = node_colors
    nodes_data["color"] = nodes_data["color"].apply(lambda x: rgb_to_hex(*x[:3]))

    node_pos_h = [map(lambda x: x * 255, pixel) for pixel in node_pos_h]
    pos = [[], [], []]
    for pixel in zip(node_pos_h, node_pos_l):
        high = tuple(pixel[0])
        low = tuple(pixel[1])
        for dim in range(3):
            cord = (high[dim] + low[dim]) / 65280
            pos[dim].append(cord)
        # print(tuple(map(lambda x: sum(x), pixel)))
    for col, dim in zip(["x", "y", "z"], pos):
        nodes_data[col] = dim
        nodes_data[col] = nodes_data[col].apply(lambda x: int(x * 1000))
        # def norm(x, dim_max):
        #     x /= dim_max
        #     return int(x)
        # dim_max = nodes_data[col].max()
        # if dim_max > 0:
        #     nodes_data[col] = nodes_data[col].apply(norm, args=(dim_max,))

    nodes_data = nodes_data.astype({"id": str})
    return nodes_data, selected_nodes


def extract_link_data(nodes: list[int], project: str):
    project_path = os.path.join(st._PROJECTS_PATH, project)
    with open(os.path.join(project_path, "links.json"), "r") as f:
        links_data = json.load(f)["links"]
    links_data = pd.DataFrame(links_data)
    if nodes:
        links_data = links_data[
            links_data["s"].isin(nodes) & links_data["e"].isin(nodes)
        ]
    links_data = links_data.rename(columns={"s": "source", "e": "target"})
    links_data["interaction"] = ["interacts" for _ in range(len(links_data))]
    links_data = links_data.astype({"source": str, "target": str})
    return links_data


if __name__ == "__main__":
    G = nx.Graph()
    G.add_edge("O15552", "Q76EI6")
    print(prepare_networkx_network(G))
