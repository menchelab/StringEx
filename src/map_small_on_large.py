import json
import os
import shutil

from .classes import Evidences as EV
from .classes import LayoutTags as LT
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import StringTags as ST
from .classes import VRNetzElements as VRNE
from .layouter import Layouter
from .settings import _MAPPING_ARBITARY_COLOR, _NETWORKS_PATH, _PROJECTS_PATH, log
from .uploader import Uploader

# def process_edge(source, sink, target_edge, source_edges):
#     edge_found = False
#     for id, edge in source_edges.items():
#         if (edge[EdgeTags.source] == source and edge[EdgeTags.sink] == sink) or (
#             edge[EdgeTags.source] == sink and edge[EdgeTags.sink] == source
#         ):
#             edge_found = True
#             for k, v in edge.items():
#                 if k not in edge:
#                     edge[k] = v
#             target_edge = edge
#             print("FOUND")
#     if not edge_found:
#         target_edge = None
#         # next_id = len(edges)
#         # source_edge[EdgeTags.source] = source
#         # source_edge[EdgeTags.sink] = sink
#         # target_net["edges"][next_id] = source_edge
#     return target_edge


def map_links(idx: int, t_link: dict, all_links: dict, target_net: dict) -> dict:
    """Add the link evidences from the string network to the ppi network.

    Args:
        idx (int): index of a link in the target network.
        t_link (dict): target link extracted from the ppi network.
        all_links (dict): contains all links from the string network.
        target_net (dict): target ppi network.

    Returns:
        dict: _description_
    """
    link = int(t_link[LiT.start]), int(t_link[LiT.end])
    if link in all_links:
        for k, v in all_links[link].items():
            if k not in t_link:
                t_link[k] = v
        target_net[VRNE.links][idx] = t_link
    return target_net


def gen_name_suid_map(source_net: dict) -> tuple[dict, dict]:
    """Maps the names and canoncial name of the nodes to nodes.

    Args:
        source_net (dict): source string network.

    Returns:
        tuple[dict, dict]: contains the map from display names to nodes and the map from canoncial names to nodes.
    """
    all_dis_names = {}
    all_canoncial_names = {}
    all_shared_names = {}
    for s_node in source_net[VRNE.nodes]:
        all_dis_names[s_node[NT.name]] = s_node
        if ST.stringdb_canoncial_name in s_node:
            all_canoncial_names[s_node[ST.stringdb_canoncial_name]] = s_node
        if ST.stringdb_shared_name in s_node:
            all_shared_names[s_node[ST.stringdb_shared_name]] = s_node
    return all_dis_names, all_canoncial_names, all_shared_names


def gen_links_map(source_net: dict) -> dict:
    """Maps the link id to the link object.

    Args:
        source_net (dict): source string network.

    Returns:
        dict: map from link id to link object.
    """
    all_links = {}
    for s_link in source_net[VRNE.links]:
        all_links[s_link[LiT.start], s_link[LiT.end]] = s_link
    return all_links


def map_nodes(
    idx: int,
    t_node: dict,
    all_dis_names: dict[str, dict],
    all_canoncial_names: dict[str, dict],
    all_shared_names: dict[str, dict],
    target: dict,
) -> tuple[dict, dict]:
    """Maps nodes from the target node to the source nodes. If a node is found, the target node receives the color of the source node. Furthermore, all annotation which the source nodes add, will be added to the target node.

    Args:
        idx (int): index of the node in the target network.
        t_node (dict): node from the target network.
        all_dis_names (dict[str,dict]): map that maps display names to node objects. Use gen_name_suid_map to generate this map.
        all_canoncial_names (dict[str,dict]): map that maps canoncial names to node objects. Use gen_name_suid_map to generate this map.
        target (dict): target ppi network.
        all_shared_names (dict[str,dict]): map that maps shared names to node objects. Use gen_name_suid_map to generate this map.
        target (dict): target ppi network.

    Returns:
        tuple: first element is the target network, second element is the source node.
    """
    t_node[NT.node_color] = _MAPPING_ARBITARY_COLOR
    node_identifiers = t_node[NT.name].split(",")
    s_node = None
    for identifier in node_identifiers:
        if identifier != "NA":
            if identifier in all_dis_names:
                s_node = all_dis_names[identifier]

            elif identifier in all_canoncial_names:
                s_node = all_canoncial_names[identifier]
            elif identifier in all_shared_names:
                s_node = all_shared_names[identifier]

            if s_node:
                t_node[NT.node_color] = s_node[NT.layouts][0][LT.color]

                for k, v in s_node.items():
                    if (
                        k not in t_node
                    ):  # Add all keys which are not yet in the node informations
                        t_node[k] = v
                    break
    target[VRNE.nodes][idx] = t_node
    return target, s_node


def map_source_to_target(
    source: str or dict,
    target: str or dict,
    target_project,
    project_name: str = "PPI_out.VRNetz",
) -> None:
    """
    Map the smaller network onto the larger network.

    Args:
        source (str or dict): Small network that will be mapped on larger target network.
        target (strordict): Large target network on which the smaller network will be mapped.
        target_project (_type_): project name from which the target network ordinates from.
        project_name (str, optional): Project name of the mapping. Defaults to "PPI_out.VRNetz".
    """

    all_dis_names, all_canoncial_names, all_shared_names = gen_name_suid_map(source)
    all_source_links = gen_links_map(source)
    updated_nodes = {}
    # ppi_to_suid = {}
    log.debug(f"{all_dis_names.keys()}")
    log.debug(f"{all_canoncial_names.keys()}")
    for idx, t_node in enumerate(target[VRNE.nodes]):
        target, s_node = map_nodes(
            idx, t_node, all_dis_names, all_canoncial_names, all_shared_names, target
        )
        if s_node:
            updated_nodes[s_node[NT.id]] = t_node
    if len(updated_nodes) == 0:
        log.error("No nodes could be mapped. Aborting")
        return (
            f'<a style="color:red;">ERROR </a>: No nodes could be mapped. Aborting',
            500,
        )
    # Check all links in the source network, whether they contain nodes that can also be found in the target network. If so, add the link to the target network and update the ids to the ids of the target network.
    links_to_consider = {}
    for link in all_source_links:
        if link[0] in updated_nodes or link[1] in updated_nodes:
            data = all_source_links[link]
            if link[0] in updated_nodes:
                t_node = updated_nodes[link[0]]  # Node in the target network
                updated = t_node[NT.id]
                link = tuple((updated, link[1]))
                data[LiT.start] = updated
            if link[1] in updated_nodes:
                t_node = updated_nodes[link[1]]  # Node in the target network
                updated = t_node[NT.id]
                link = tuple((link[0], updated))
                data[LiT.end] = updated
            links_to_consider[link] = data

    for idx, t_link in enumerate(target[VRNE.links]):
        target = map_links(idx, t_link, links_to_consider, target)
    uploader = Uploader(target, project_name)
    uploader.color_nodes(target_project)
    return f'<a style="color:green;" href="/StringEx/preview?project={project_name}">SUCCESS: Saved as project {project_name} </a>'


if __name__ == "__main__":
    string_network = "/Users/till/Desktop/2000_alzheimer.VRNetz"
    PPI_VrNet = (
        "/Users/till/Documents/Playground/STRING-VRNetzer/static/networks/PPI.VrNetz"
    )
    map_source_to_target(string_network, PPI_VrNet)
    # /opt/homebrew/bin/python3 /Users/till/Documents/Playground/STRING-VRNetzer/src/main.py project '/Users/till/Documents/Playground/STRING-VRNetzer/static/networks/PPI_out.VrNetz' None None False 2000_alz_map_ppi_with_ev False False
