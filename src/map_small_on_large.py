import json
import os
import shutil

from .settings import _MAPPING_ARBITARY_COLOR, _NETWORKS_PATH, _PROJECTS_PATH
from .settings import Evidences as EV
from .settings import LayoutTags as LT
from .settings import LinkTags as LiT
from .settings import NodeTags as NT
from .settings import StringTags as ST
from .settings import VRNetzElements as VRNE
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


def map_links(idx, t_link: dict, all_links: dict, target_net: dict) -> dict:
    """Add the link evidences from the string network to the ppi network"""
    link = int(t_link[LiT.start]), int(t_link[LiT.end])
    if link in all_links:
        for k, v in all_links[link].items():
            if k not in t_link:
                t_link[k] = v
        target_net[VRNE.links][idx] = t_link
    return target_net


def gen_name_suid_map(source_net: dict) -> tuple[dict, dict]:
    all_dis_names = {}
    all_canoncial_names = {}
    for s_node in source_net[VRNE.nodes]:
        all_dis_names[s_node[NT.name]] = s_node
        if ST.stringdb_canoncial_name in s_node:
            all_canoncial_names[s_node[ST.stringdb_canoncial_name]] = s_node
    return all_dis_names, all_canoncial_names


def gen_links_map(source_net: dict) -> dict:
    all_links = {}
    for s_link in source_net[VRNE.links]:
        all_links[s_link[LiT.start], s_link[LiT.end]] = s_link
    return all_links


def map_values(idx, t_node, all_dis_names, all_canoncial_names, target) -> dict:
    """Adds the values from the String Network onto the node in the PPI"""
    arbitrary_color = _MAPPING_ARBITARY_COLOR
    t_node[NT.node_color] = arbitrary_color
    node_identifiers = t_node[NT.name].split(",")
    for identifier in node_identifiers:
        if identifier != "NA":
            s_node = None
            if identifier in all_dis_names:
                s_node = all_dis_names[identifier]

            elif identifier in all_canoncial_names:
                s_node = all_canoncial_names[identifier]
            if s_node:
                t_node[NT.node_color] = s_node[NT.layouts][0][LT.color]
                for k, v in s_node.items():
                    if (
                        k not in t_node
                    ):  # Add all keys which are not yet in the node informations
                        t_node[k] = v

    target[VRNE.nodes][idx] = t_node
    return target, s_node

def map_source_to_target(
    source: str or dict, target: str or dict,target_project, project_name: str = "PPI_out.VRNetz",
) -> None:
    """
    Map the smaller network onto the larger network.

    Args:
        source (str or dict): Small network that will be mapped on larger target network.
        target (strordict): Large target network on which the smaller network will be mapped.
        target_project (_type_): project name from which the target network ordinates from.
        project_name (str, optional): Project name of the mapping. Defaults to "PPI_out.VRNetz".
    """

    all_dis_names, all_canoncial_names = gen_name_suid_map(source)
    all_links = gen_links_map(source)
    updated_nodes = {}
    # ppi_to_suid = {}
    for idx, t_node in enumerate(target[VRNE.nodes]):
        target,s_node = map_values(idx, t_node, all_dis_names, all_canoncial_names, target)
        if s_node:
            updated_nodes[s_node[NT.id]] = t_node
    old_links = all_links.copy()
    for link in old_links:
        if link[0] in updated_nodes or link[1] in updated_nodes:
            data = all_links[link]
            all_links.pop(link)
            if link[0] in updated_nodes:
                link = tuple((updated_nodes[link[0]][NT.id],link[1]))
            if link[1] in updated_nodes:
                link = tuple((link[0],updated_nodes[link[1]][NT.id]))

        all_links[link] = data
    print(all_links.keys())
    for idx, t_link in enumerate(target[VRNE.links]):
        target = map_links(idx, t_link, all_links, target)
    
    uploader = Uploader(target,project_name)
    uploader.color_nodes(target_project)


if __name__ == "__main__":
    string_network = "/Users/till/Desktop/2000_alzheimer.VRNetz"
    PPI_VrNet = (
        "/Users/till/Documents/Playground/STRING-VRNetzer/static/networks/PPI.VrNetz"
    )
    map_source_to_target(string_network, PPI_VrNet)
    # /opt/homebrew/bin/python3 /Users/till/Documents/Playground/STRING-VRNetzer/src/main.py project '/Users/till/Documents/Playground/STRING-VRNetzer/static/networks/PPI_out.VrNetz' None None False 2000_alz_map_ppi_with_ev False False
