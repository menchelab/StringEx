import glob
import json
import os
import shutil
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from PIL import Image

from .classes import Evidences as EV
from .classes import LayoutTags as LT
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import StringTags as ST
from .classes import VRNetzElements as VRNE
from .layouter import Layouter
from .settings import (
    _MAPPING_ARBITARY_COLOR,
    _NETWORKS_PATH,
    _PROJECTS_PATH,
    MAX_NUM_LINKS,
    log,
)
from .uploader import Uploader
import pandas as pd



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
    all_shorts = {}
    for s_node in source_net[VRNE.nodes]:
        all_dis_names[s_node[NT.name]] = s_node
        if ST.stringdb_canoncial_name in s_node:
            all_canoncial_names[s_node[ST.stringdb_canoncial_name]] = s_node
        if ST.stringdb_shared_name in s_node:
            all_shared_names[s_node[ST.stringdb_shared_name]] = s_node
            try:
                all_shorts[s_node[ST.stringdb_shared_name].split(".")[1]] = s_node
            except Exception:
                pass
            # FIXME: this is a hack to get the short name of the protein

    return all_dis_names, all_canoncial_names, all_shared_names, all_shorts


def gen_link_maps(source_net: dict, target_net: dict) -> tuple[dict, dict]:
    """Maps the link id to the link object.

    Args:
        source_net (dict): source string network.

    Returns:
        tuple[dict,dict]: maps from link id to link object.
    """
    all_source_links, all_target_links = {}, {}
    dicts = [all_source_links, all_target_links]
    nets = [source_net, target_net]
    for dictionary, net in zip(dicts, nets):
        for link in net[VRNE.links]:
            dictionary[link[LiT.start], link[LiT.end]] = link
    return all_source_links, all_target_links


def map_nodes(
    idx: int,
    t_node: dict,
    all_dis_names: dict[str, dict],
    all_canoncial_names: dict[str, dict],
    all_shared_names: dict[str, dict],
    all_shorts: dict[str, dict],
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
    s_node = None
    for identifier in t_node["attrlist"]:
        if identifier == "":
            continue
        if identifier in all_dis_names:
            s_node = all_dis_names[identifier]
        elif identifier in all_canoncial_names:
            s_node = all_canoncial_names[identifier]
        elif identifier in all_shared_names:
            s_node = all_shared_names[identifier]
        elif identifier in all_shorts:
            s_node = all_shorts[identifier]

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
    source
    target
    # map all links from source to links on target and expand the target links
    src_nodes = pd.DataFrame(source[VRNE.nodes])
    target_nodes = pd.DataFrame(target[VRNE.nodes])

    def get_short(x):
        try:
            return x.split(".")[1]
        except:
            return x

    target_nodes["n"] = target_nodes["attrlist"].apply(
        lambda x: x[0] if isinstance(x, list) else pd.NA
    )
    target_nodes["uniprot"] = target_nodes["attrlist"].apply(
        lambda x: [x[1]] if isinstance(x, list) and len(x) > 1 else pd.NA
    )
    target_nodes["description"] = target_nodes["attrlist"].apply(
        lambda x: x[2] if isinstance(x, list) and len(x) > 2 and x[2] != "" else pd.NA
    )

    if "stringdb_database identifier" in src_nodes:
        src_nodes["short"] = src_nodes["stringdb_database identifier"].apply(get_short)
    if "stringdb_description" in src_nodes:
        src_nodes = src_nodes.rename(columns={"stringdb_description": "description"})

    def get_id_on_taget(x, target_nodes):
        tests = []
        for identifier in [
            "name",
            "display_name",
            "stringdb_database identifier",
            "short",
            "stringdb_canonical name",
            "shared name",
            "uniprot",
        ]:
            if identifier in x:
                tests.append(identifier)
        s_node = pd.NA
        while s_node is pd.NA and len(tests) > 0:
            query = tests.pop()
            s_node = target_nodes["attrlist"].apply(lambda y: x[query] in y)
            if s_node.any():
                s_node = int(s_node[s_node == True].index[0])
                return s_node
            else:
                s_node = pd.NA
        return s_node

    src_nodes["target_id"] = src_nodes.apply(
        get_id_on_taget, axis=1, args=(target_nodes,)
    )

    src_nodes["c"] = src_nodes.apply(lambda x: x["layouts"][0][NT.node_color] if "layouts" in x else x["cy_col"], axis=1)
    if "layouts" in src_nodes.columns:
        src_nodes = src_nodes.drop(columns="layouts")

    # merge reindex into target_nodes 
    updated = src_nodes[src_nodes["target_id"].notna()]
    cols =[c for c in src_nodes.columns if c not in target_nodes.columns or c in ["uniprot,description"]]
    new_cols = updated[cols]
    new_cols.index = new_cols["target_id"]
    target_nodes = target_nodes.merge(new_cols,how="outer",left_index=True,right_index=True)
    target_nodes["c"] = target_nodes["c"].fillna({ i:_MAPPING_ARBITARY_COLOR for i in target_nodes.index})

    if len(updated) == 0:
        log.error("No nodes could be mapped. Aborting")
        return (
            f'<a style="color:red;">ERROR </a>: No nodes could be mapped. Is this the correct organism you want to map on? Aborting',
            500,
        )

    log.debug(f"Updated {len(updated)} nodes")
    src_links = pd.DataFrame(source[VRNE.links])
    if ST.stringdb_score in src_links:
        src_links = src_links.rename(columns={ST.stringdb_score: EV.any.value})
    drops = [c for c in ["s_suid", "e_suid","SUID"] if c in src_links]
    if len(drops) > 0:
        src_links = src_links.drop(columns=drops)
    target_links = pd.DataFrame(target[VRNE.links])

    def check_if_in_target(x, src_nodes):
        start_node = src_nodes[src_nodes["id"] == x[LiT.start]]
        end_node = src_nodes[src_nodes["id"] == x[LiT.end]]
        if start_node["target_id"] is not pd.NA and end_node["target_id"] is not pd.NA:
            x[LiT.start] = int(start_node["target_id"])
            x[LiT.end] = int(end_node["target_id"])
        return x

    src_links = src_links.apply(check_if_in_target, axis=1, args=(src_nodes,))
    def find_link_in_target(x, target_links):
        index = target_links[
            (target_links[LiT.start] == x[LiT.start])
            & (target_links[LiT.end] == x[LiT.end])
        ].index
        if len(index) > 0:
            return index[0]
        return None
    src_links["target_id"] = src_links.apply(find_link_in_target, axis=1, args=(target_links,))
    add = src_links[src_links["target_id"].isna()]
    updated = src_links[src_links["target_id"].notna()]
    new_cols = updated[[c for c in src_links.columns if c not in target_links.columns]]

    new_cols.index = new_cols["target_id"]
    target_links = target_links.merge(new_cols,how="outer",left_index=True,right_index=True)

    target_links = target_links.drop(columns=["target_id"])
    target_links = pd.concat([target_links,add])
    target_links = target_links.reset_index(drop=True)
    target_links = Layouter.gen_evidence_layouts(target_links)


    target = {VRNE.nodes: target_nodes, VRNE.links: target_links}

    uploader = Uploader(target, project_name)
    uploader.color_nodes(target_project)
    log.info(f"Saving project {project_name}")
    return f'<a style="color:green;" href="/StringEx/preview?project={project_name}" target="_blank">SUCCESS: Saved as project {project_name} </a>'

if __name__ == "__main__":
    string_network = "/Users/till/Desktop/2000_alzheimer.VRNetz"
    PPI_VrNet = (
        "/Users/till/Documents/Playground/STRING-VRNetzer/static/networks/PPI.VrNetz"
    )
    map_source_to_target(string_network, PPI_VrNet)
    # /opt/homebrew/bin/python3 /Users/till/Documents/Playground/STRING-VRNetzer/src/main.py project '/Users/till/Documents/Playground/STRING-VRNetzer/static/networks/PPI_out.VrNetz' None None False 2000_alz_map_ppi_with_ev False False
