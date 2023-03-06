import json
import os
import random

import GlobalData as GD
import pandas as pd
import py4cytoscape as p4c
import requests
from PIL import Image

from . import settings as st
from . import util as string_util
from .classes import NodeTags as NT
from project import Project


def send_to_cytoscape(message, ip, user, return_dict, pfile, project) -> None:
    """Send the selected nodes to Cytoscape.

    Args:
        message (dict): Message from the frontend.
        ip (str): IP address of the client.
        user (str): Username of the client.
        return_dict (dict): Dictionary to store the return value.

    Returns:
        dict: Dictionary with the status of the process stored in the return_dict.
    """
    return_dict["status"] = {
        "message": f"No node or link is selected.",
        "status": "error",
    }
    sate_data = pfile.get("stateData")
    if sate_data is None:
        return
    selected = sate_data.get("selected")
    selected_links = sate_data.get("selectedLinks")
    if selected is None:
        selected = []
    if selected_links is None:
        selected_links = []
    if len(selected) == 0 and len(selected_links) == 0:
        return

    port = 1234
    layout = message.get("layout", "")
    color = message.get("color", "")
    title = f"{layout} & {color}"
    base_url = "http://" + str(ip) + f":{port}/v1"

    try:
        p4c.cytoscape_ping(base_url=base_url)
    except requests.exceptions.RequestException:
        return_dict["status"] = {
            "message": f"Could not connect to Cytoscape at {base_url}. Please check if Cytoscape is running and if the url is correct. Is cyREST installed?",
            "status": "error",
        }
        return
    if len(selected) == 0:
        st.log.debug("No nodes selected.")
        links, selected = extract_link_data(selected, selected_links, project)
        nodes = extract_node_data(selected, selected_links, project, layout, color)
    else:
        nodes = extract_node_data(selected, project, layout, color)
        links, _ = extract_link_data(selected, selected_links, project)

    st.log.debug("Extracted node and link data", flush=True)
    # Create network
    args = (nodes,)
    if links.size > 0:
        args += (links,)
    try:
        suid = p4c.create_network_from_data_frames(
            *args, base_url=base_url, collection=project, title=title
        )
        st.log.debug(f"Created network with SUID: {suid}")

        # Create style
        style = "VRNetzer_Style"
        if style not in p4c.get_visual_style_names(
            base_url=base_url,
        ):
            p4c.create_visual_style(style, base_url=base_url)
            st.log.debug(f"Created style: {style}", flush=True)

        # Set colors
        p4c.set_node_color_mapping(
            default_color="black",
            table_column="color",
            mapping_type="p",
            style_name=style,
            base_url=base_url,
            network=suid,
        )
        st.log.debug(f"Set node color mapping", flush=True)

        # Set layout
        values = ["name", "size", "x", "y"]
        properties = ["NODE_LABEL", "NODE_SIZE", "NODE_X_LOCATION", "NODE_Y_LOCATION"]
        if "NODE_Z_LOCATION" in p4c.get_visual_property_names():
            values.append("z")
            properties.append("NODE_Z_LOCATION")

        for property, column in zip(properties, values):
            mapping = p4c.map_visual_property(
                property,
                table_column=column,
                mapping_type="p",
                base_url=base_url,
                network=suid,
            )
            p4c.update_style_mapping(style, mapping, base_url=base_url)
            st.log.debug(f"Set {property} mapping", flush=True)

        # Set style
        p4c.set_visual_style(style, base_url=base_url, network=suid)
        st.log.debug(f"Set style: {style}", flush=True)

        # Fit content
        p4c.fit_content(base_url=base_url, network=suid)
        st.log.debug(f"Fit content", flush=True)
        st.log.debug(f"Created new network in Cytoscape at client {ip}:{port}")
        return_dict["status"] = {
            "message": f"Project {project} successfully send to Cytoscape.",
            "status": "success",
        }

    except Exception as e:
        if isinstance(e, p4c.exceptions.CyError):
            st.log.debug(f"Could not send project to Cytoscape. {e}", flush=True)
            return_dict["status"] = {
                "message": f"Could not send project to Cytoscape. {e}. Network has been removed from Cytoscape!",
                "status": "error",
            }
        elif isinstance(e, requests.exceptions.RequestException):
            st.log.debug(f"Could not send project to Cytoscape. {e}", flush=True)
            return_dict["status"] = {
                "message": f"Could not connect to Cytoscape at {base_url}. Please check if Cytoscape is running and if the url is correct. Is cyREST installed?",
                "status": "error",
            }


def extract_node_data(
    selected_nodes: list[int], project: str, layout: str, color: str
) -> tuple[pd.DataFrame, list[int]]:
    """Extract node data of selected nodes from selected layout and color as well as other node attributes from the nodes file and the name from the names.json file.

    Args:
        selected_nodes (list[int]): Selected nodes to extract data from.
        project (str): Project name.
        layout (str): Layout to extract node positions from.
        color (str): Color texture to extract node colors and size from.

    Returns:
        tuple(pd.DataFrame,list[int]): Nodes data and selected nodes as nodes list gets reduced to a total of maximal 2000 nodes.
    """
    project = Project(project)
    project.read_nodes()
    project.read_names()
    nodes_data = pd.DataFrame(project.nodes["nodes"])
    nodes_data = nodes_data[nodes_data.index.isin(selected_nodes)].copy()

    if "layouts" in nodes_data.columns:
        nodes_data = nodes_data.drop(columns=["layouts"])

    if "display name" in nodes_data.columns:
        nodes_data["name"] = nodes_data["display name"]
        nodes_data = nodes_data.drop(columns=["display name", NT.name])

    names = project.names["names"]
    annot_len = len(names[0])
    nodes_data["name"] = [names[x][0] for x in nodes_data.index]
    if annot_len >= 2:
        nodes_data["uniprot"] = [names[x][1] for x in nodes_data.index]
        for annot in range(2, len(names[0])):
            nodes_data[f"annotation{annot}"] = [
                names[x][annot] for x in nodes_data.index
            ]

    if layout not in project.pfile["layouts"]:
        layout = project.pfile["layouts"][0]

    if color not in project.pfile["layoutsRGB"]:
        color = project.pfile["layoutsRGB"][0]

    node_pos_l = list(
        Image.open(os.path.join(project.location, "layouts", layout + ".bmp")).getdata()
    )

    node_pos_h = list(
        Image.open(
            os.path.join(project.location, "layoutsl", layout + "l.bmp")
        ).getdata()
    )

    node_colors = list(
        Image.open(
            os.path.join(project.location, "layoutsRGB", color + ".png")
        ).getdata()
    )

    node_colors = [node_colors[c] for c in nodes_data.index]
    node_pos_l = [node_pos_l[c] for c in nodes_data.index]
    node_pos_h = [node_pos_h[c] for c in nodes_data.index]

    def rgb_to_hex(r, g, b):
        return "#{:02x}{:02x}{:02x}".format(r, g, b)

    st.log.debug(f"{len(nodes_data)}, {len(node_colors)}")
    nodes_data["color"] = node_colors
    nodes_data["size"] = (
        nodes_data["color"].swifter.progress_bar(False).apply(lambda x: x[-1])
    )
    nodes_data["size"].astype("int64")
    nodes_data["color"] = (
        nodes_data["color"]
        .swifter.progress_bar(False)
        .apply(lambda x: rgb_to_hex(*x[:3]))
    )

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
        nodes_data[col] = (
            nodes_data[col].swifter.progress_bar(False).apply(lambda x: int(x * 1000))
        )
    if "n" in nodes_data.columns:
        nodes_data = nodes_data.drop(columns=["n"])
    nodes_data["shared name"] = nodes_data["name"].copy()
    nodes_data = nodes_data.astype({"id": str})
    return nodes_data


def extract_link_data(
    nodes: list[int], selected_links: list[int], project: str
) -> pd.DataFrame:
    """Extracts links from projects links.json file.

    Args:
        nodes (list[int]): IDs of selected nodes.
        project (str): project name.

    Returns:
        pd.DataFrame: Extracted link data.
    """
    project_path = os.path.join(st._PROJECTS_PATH, project)
    with open(os.path.join(project_path, "links.json"), "r") as f:
        links_data = json.load(f)["links"]
    links_data = pd.DataFrame(links_data)
    if selected_links:
        links_data = links_data[links_data.index.isin(selected_links)]
    if nodes:
        links_data = links_data[
            links_data["s"].isin(nodes) & links_data["e"].isin(nodes)
        ]
    else:
        all_links = pd.concat(links_data["s"], links_data["e"])
        nodes = all_links.unique()
    links_data = links_data.rename(columns={"s": "source", "e": "target"})
    links_data["interaction"] = ["interacts" for _ in range(len(links_data))]
    links_data = links_data.astype({"source": str, "target": str})
    return links_data, nodes
