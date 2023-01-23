import glob
import json
import os
import shutil

from PIL import Image

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


def map_links(t_link: dict, s_link: dict) -> dict:
    """Add the link evidences from the string network to the ppi network.

    Args:
        t_link (dict): target link extracted from the ppi network.
        s_link (dict): source link extracted from the string network.
    Returns:
        dict: updated link dict
    """
    for k, v in s_link.items():
        if k not in t_link:
            t_link[k] = v
    return t_link


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


def gen_link_maps(source_net: dict, target_net: dict) -> tuple[dict, dict]:
    """Maps the link id to the link object.

    Args:
        source_net (dict): source string network.

    Returns:
        tuple[dict,dict]: maps from link id to link object.
    """
    all_soruce_links, all_target_links = {}, {}
    dicts = [all_soruce_links, all_target_links]
    nets = [source_net, target_net]
    for dictionary, net in zip(dicts, nets):
        for link in net[VRNE.links]:
            dictionary[link[LiT.start], link[LiT.end]] = link
    return all_soruce_links, all_target_links


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
                    ):  # Add all keys which are not yet in the node information
                        t_node[k] = v
                break
    target[VRNE.nodes][idx] = t_node
    return target, s_node


def extract_link_data(
    x: int,
    y: int,
    rgb_x: int,
    rgb_y: int,
    tex: Image,
    links: dict,
    evidence: str or None,
    rgb: Image or None,
    next_idx: int,
) -> dict[tuple, dict]:
    """Extracts the data for a link from an texture Image and its rgb Image.

    Args:
        x (int): horizontal pixel in the texture image.
        y (int): vertical pixel in the texture image.
        rgb_x (int): horizontal pixel in the rgb image.
        rgb_y (int): vertical pixel in the rgb image.
        tex (Image): texture image object.
        links (dict): dictionary containing all links with a tuple of start, and end as keys and the link itself as value.
        evidence (str o rNone): string evidence of the current layout.
        rgb (Image or None): rgb image object.
        next_idx (int): next index for the link id.
    Returns:
        dict[tuple, dict]: dictionary containing all links with a tuple of start, and end as keys and the link itself as value.
    """
    start_p = tex.getpixel((x, y))
    if x + 1 < tex.width:
        end_p = tex.getpixel((x + 1, y))
    else:
        end_p = tex.getpixel((0, y + 1))
    if start_p == (0, 0, 0):
        return True, next_idx, rgb_x, rgb_y, links
    start = start_p[0] + start_p[1] * 128 + start_p[2] * 128 * 128
    end = end_p[0] + end_p[1] * 128 + end_p[2] * 128 * 128
    if tuple((start, end)) not in links:
        link = {
            LiT.id: next_idx,
            LiT.start: start,
            LiT.end: end,
        }
        links[tuple((start, end))] = link
        next_idx += 1
    else:
        link = links[tuple((start, end))]
    link = links[tuple((start, end))]
    if rgb:
        color = rgb.getpixel((rgb_x, rgb_y))
        rgb_x += 1
        if rgb_x >= rgb.width:
            rgb_x = 0
            rgb_y += 1
        if evidence:
            score = color[3] / 255
            link[evidence] = score
    return False, next_idx, rgb_x, rgb_y, links


def extract_links_from_tex(link_texs: str, link_rgbs: str) -> list[dict]:
    """extract links from the links texture and the color from linkRGB.

    Args:
        link_texs (str): path to the directory which contains the link textures of the project.
        link_rgbs (str): path to the directory which contains the linkrgb textures of the project.

    Returns:
        list[dict]: contains all extracted links.
    """
    links = {}
    next_idx = 0
    for file in glob.glob(link_texs):
        evidence = None
        rgb = None
        rgb_file = None
        for ev in EV:
            ev = ev.value
            if ev in file:
                evidence = ev
                for rf in glob.glob(link_rgbs):
                    if evidence in rf:
                        rgb_file = rf
                        break
                break
        tex = Image.open(file)
        if rgb_file:
            rgb = Image.open(rgb_file)
        rgb_x, rgb_y = 0, 0
        all_link_done = False
        for y in range(tex.height):
            for x in range(0, tex.width, 2):
                all_link_done, next_idx, rgb_x, rgb_y, links = extract_link_data(
                    x, y, rgb_x, rgb_y, tex, links, evidence, rgb, next_idx
                )
                if all_link_done:
                    break
            if all_link_done:
                break
    return list(links.values())


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
    all_source_links, all_target_links = gen_link_maps(source, target)
    updated_nodes = {}
    # ppi_to_suid = {}
    # log.debug(f"{all_dis_names.keys()}")
    # log.debug(f"{all_canoncial_names.keys()}")
    for idx, t_node in enumerate(target[VRNE.nodes]):
        target, s_node = map_nodes(
            idx, t_node, all_dis_names, all_canoncial_names, all_shared_names, target
        )
        if s_node:
            updated_nodes[s_node[NT.id]] = t_node
            target[VRNE.nodes][idx] = t_node
    if len(updated_nodes) == 0:
        log.error("No nodes could be mapped. Aborting")
        return (
            f'<a style="color:red;">ERROR </a>: No nodes could be mapped. Is this the correct organism you want to map on? Aborting',
            500,
        )
    # # Used when all unmapped nodes are also added with a calculated layout
    # next_idx = idx + 1
    # new_nodes = {}
    # for s_node in source[VRNE.nodes]:
    #     if s_node[NT.id] not in updated_nodes:
    #         old_id = s_node[NT.id]
    #         s_node[NT.id] = next_idx
    #         next_idx += 1
    #         new_nodes[old_id] = s_node
    log.debug(f"Updated {len(updated_nodes)} nodes")
    # log.debug(f"Will add {len(all_source_links)} new nodes")     # Used when all unmapped nodes are also added with a calculated layout

    # Check all links in the source network, whether they contain nodes that can also be found in the target network. If so, add the link to the target network and update the ids to the ids of the target network.

    links_to_consider = {}
    # new_links = {} # Used when all unmapped nodes are also added with a calculated layout
    for link, data in all_source_links.items():
        if link[0] in updated_nodes or link[1] in updated_nodes:
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
        # # Used when all unmapped nodes are also added with a calculated layout
        # elif link[0] in new_nodes and link[1] in new_nodes:
        #     if link[0] in new_nodes:
        #         s_node = new_nodes[link[0]]
        #         updated = s_node[NT.id]
        #         link = tuple((updated, link[1]))
        #         data[LiT.start] = updated
        #     if link[1] in new_nodes:
        #         s_node = new_nodes[link[1]]
        #         updated = s_node[NT.id]
        #         link = tuple((link[0], updated))
        #         data[LiT.end] = updated
        #     new_links[link] = data

    nxt_idx = len(target)
    for idx, s_link in enumerate(links_to_consider):
        if s_link in all_target_links:
            t_link = all_target_links[s_link]
            l_idx = t_link[LiT.id]
            s_link = links_to_consider[s_link]
            target[VRNE.links][l_idx] = map_links(t_link, s_link)
            # log.debug(f"updated link:{l_idx}")
        else:
            s_link = links_to_consider[s_link]
            s_link[LiT.id] = nxt_idx
            # log.debug(f"Added link:{nxt_idx}")
            target[VRNE.links].append(s_link)
            nxt_idx += 1

    # # Used when all unmapped nodes are also added with a calculated layout
    # for _, data in new_links.items:
    #     data[LiT.id] = nxt_idx
    #     # log.debug(f"Added link:{nxt_idx}")
    #     target[VRNE.links].append(data)
    #     nxt_idx += 1

    target = {VRNE.nodes: target[VRNE.nodes], VRNE.links: target[VRNE.links]}
    target = Layouter.gen_evidence_layouts(target)
    nb = 0
    for link in target[VRNE.links]:
        if EV.stringdb_neighborhood.value in link:
            nb += 1
    uploader = Uploader(target, project_name)
    uploader.color_nodes(target_project, None)
    return f'<a style="color:green;" href="/StringEx/preview?project={project_name}">SUCCESS: Saved as project {project_name} </a>'


if __name__ == "__main__":
    string_network = "/Users/till/Desktop/2000_alzheimer.VRNetz"
    PPI_VrNet = (
        "/Users/till/Documents/Playground/STRING-VRNetzer/static/networks/PPI.VrNetz"
    )
    map_source_to_target(string_network, PPI_VrNet)
    # /opt/homebrew/bin/python3 /Users/till/Documents/Playground/STRING-VRNetzer/src/main.py project '/Users/till/Documents/Playground/STRING-VRNetzer/static/networks/PPI_out.VrNetz' None None False 2000_alz_map_ppi_with_ev False False
