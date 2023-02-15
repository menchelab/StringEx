import warnings

import swifter

warnings.simplefilter(action="ignore", category=FutureWarning)

import pandas as pd
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


def map_nodes(
    src_nodes: pd.DataFrame, target_nodes: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map nodes from the source network to the target network. Only nodes found in the target network are mapped. Mapped nodes will be updated with additional attributes from the source network.

    Args:
        src_nodes (pd.DataFrame): All nodes from the source network.
        target_nodes (pd.DataFrame): All nodes from the target network.
    Return:
        tuple[pd.DataFrame,pd.DataFrame]: Mapped nodes and target nodes with additional attributes from the source network.
    """

    target_nodes["n"] = target_nodes["attrlist"].swifter.apply(
        lambda x: x[0] if isinstance(x, list) else pd.NA
    )
    target_nodes["uniprot"] = target_nodes["attrlist"].swifter.apply(
        lambda x: [x[1]] if isinstance(x, list) and len(x) > 1 else pd.NA
    )
    target_nodes["description"] = target_nodes["attrlist"].swifter.apply(
        lambda x: x[2] if isinstance(x, list) and len(x) > 2 and x[2] != "" else pd.NA
    )

    # Split identifier into taxid and gene name
    if "stringdb_database identifier" in src_nodes:

        def get_short(x):
            splitted = x.split(".")
            if len(splitted) > 1:
                return splitted[1]
            return x

        src_nodes["short"] = src_nodes["stringdb_database identifier"].swifter.apply(
            get_short
        )
        log.debug("Split identifier into taxid and gene name!")

    # rename to general key name
    if "stringdb_description" in src_nodes:
        src_nodes = src_nodes.rename(columns={"stringdb_description": "description"})
        log.debug("Renamed description column!")

    def get_id_on_taget(x: pd.Series, target_nodes: pd.DataFrame):
        """Extract the node from the target network that matches with at least one identifier from the source node.

        Args:
            x (pd.Series): src node
            target_nodes (pd.DataFrame): all target nodes

        Returns:
            _type_: _description_
        """
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
            for col in attribute.columns:
                column = attribute[col].to_list()
                if not x[query] in column:
                    continue
                s_node = column.index(x[query])
        return s_node

    def extract_attributes(x: pd.Series):
        num_attr = len(x)
        res = pd.Series([pd.NA] * num_attr)
        for i, a in enumerate(x):
            res[i] = a
        return res

    attribute = target_nodes["attrlist"].swifter.apply(extract_attributes)
    src_nodes["target_id"] = src_nodes.swifter.apply(
        get_id_on_taget, axis=1, args=(attribute,)
    )

    src_nodes["c"] = src_nodes.swifter.apply(
        lambda x: x["layouts"][0][NT.node_color] if "layouts" in x else x["cy_col"],
        axis=1,
    )
    if "layouts" in src_nodes.columns:
        src_nodes = src_nodes.drop(columns="layouts")

    # merge reindex into target_nodes
    src_nodes = src_nodes[src_nodes["target_id"].notna()]
    cols = [
        c
        for c in src_nodes.columns
        if c not in target_nodes.columns or c in ["uniprot,description"]
    ]
    new_cols = src_nodes[cols]
    new_cols.index = new_cols["target_id"]
    target_nodes = target_nodes.merge(
        new_cols, how="outer", left_index=True, right_index=True
    )
    target_nodes["c"] = target_nodes["c"].fillna(
        {i: _MAPPING_ARBITARY_COLOR for i in target_nodes.index}
    )

    if len(src_nodes) == 0:
        log.error("No nodes could be mapped. Aborting")
        return (
            f'<a style="color:red;">ERROR </a>: No nodes could be mapped. Is this the correct organism you want to map on? Aborting',
            500,
        )

    log.debug(f"Updated {len(src_nodes)} nodes")
    return src_nodes, target_nodes


def map_links(
    src_links: pd.DataFrame, target_links: pd.DataFrame, src_nodes: pd.DataFrame
) -> pd.DataFrame:
    """Map and update links from source to target network. If link is not in target network, but its start and end node are, add a new link.

    Args:
        src_links (pd.DataFrame): All links from the source network.
        target_links (pd.DataFrame): All links from the target network.
        src_nodes (pd.DataFrame): All nodes which are mapped from the source network onto the target network.

    Returns:
        pd.DataFrame: Updated links from the target network.
    """

    if ST.stringdb_score in src_links:
        src_links = src_links.rename(columns={ST.stringdb_score: EV.any.value})

    drops = [c for c in ["s_suid", "e_suid", "SUID"] if c in src_links]
    if len(drops) > 0:
        src_links = src_links.drop(columns=drops)

    def check_if_in_target(x: pd.Series, src_nodes: pd.DataFrame) -> pd.Series:
        """Looks whether the link is in the target network. If so, the start and end id of the link are updated to match the ones in the target network.

        Args:
            x (pd.Series): src links.
            src_nodes (pd.DataFrame): contains all mapped nodes.

        Returns:
            pd.Series: updated link.
        """
        start_node = src_nodes[src_nodes["id"] == x[LiT.start]]
        end_node = src_nodes[src_nodes["id"] == x[LiT.end]]
        x[LiT.start] = int(start_node["target_id"])
        x[LiT.end] = int(end_node["target_id"])
        return x

    # only consider links where start and end are mapped
    node_ids = src_nodes["id"].to_list()

    src_links = src_links[
        src_links[LiT.start].isin(node_ids) & src_links[LiT.end].isin(node_ids)
    ]
    log.debug(f"Considering {len(src_links)} links.")

    src_links = src_links.swifter.apply(check_if_in_target, axis=1, args=(src_nodes,))

    log.debug(f"Filtering target links to only consider mapped nodes...")

    node_target_ids = src_nodes["target_id"].to_list()
    filter = target_links[LiT.start].isin(node_target_ids) & target_links[LiT.end].isin(
        node_target_ids
    )

    links_to_consider = target_links[filter]
    log.debug(f"Filtered!")

    log.debug(f"Finding index of link in target...")

    def find_link_in_target(x: pd.Series, to_consider: pd.DataFrame) -> int or None:
        """Extract the link from the target network that matches with the source links and updated the source link accordingly.

        Args:
            x (pd.Series): source link
            to_consider (pd.DataFrame): DataFrame with all links in which a the start and the end node are mapped.

        Returns:
            int or None: in case the link is found, the index of the link in the target network is returned. Otherwise None is returned.
        """
        index = to_consider[
            (to_consider[LiT.start] == x[LiT.start])
            & (to_consider[LiT.end] == x[LiT.end])
        ].index
        if len(index) > 0:
            return index[0]
        return None

    src_links["target_id"] = src_links.swifter.apply(
        find_link_in_target, axis=1, args=(links_to_consider,)
    )
    log.debug(f"All indices found!")

    add = src_links[src_links["target_id"].isna()]
    update = src_links[src_links["target_id"].notna()]

    new_cols = update[[c for c in update.columns if c not in target_links.columns]]

    log.debug(f"Updating target links...")
    new_cols.index = new_cols["target_id"]
    target_links = target_links.merge(
        new_cols, how="outer", left_index=True, right_index=True
    )

    log.debug(f"Links updated!")

    target_links = target_links.drop(columns=["target_id"])

    # all links that are not in the target network, but have mapped start and end nodes.
    target_links = pd.concat([target_links, add])
    target_links = target_links.reset_index(drop=True)
    target_links = Layouter.gen_evidence_layouts(
        target_links
    )  # Transform stringdb scores to evidence values

    return target_links


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
    src_nodes = pd.DataFrame(source[VRNE.nodes])
    target_nodes = pd.DataFrame(target[VRNE.nodes])

    src_nodes, target_nodes = map_nodes(src_nodes, target_nodes)

    src_links = pd.DataFrame(source[VRNE.links])
    target_links = pd.DataFrame(target[VRNE.links])

    target_links = map_links(src_links, target_links, src_nodes)

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
