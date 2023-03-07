import warnings

import swifter

warnings.simplefilter(action="ignore", category=FutureWarning)

import pandas as pd
from PIL import Image

from .classes import Evidences as EV
from .classes import LayoutTags as LT
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import StringTags as ST, CytoscapeTags as CT
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
    # Split identifier into taxid and gene name
    if ST.stringdb_identifier in src_nodes:

        src_nodes["short"] = (
            src_nodes["stringdb_database identifier"]
            .swifter.progress_bar(False)
            .apply(lambda x: x.split(".")[1] if len(x.split(".")) > 1 else x)
        )
        log.debug("Split identifier into taxid and gene name!", flush=True)

    # rename to general key name
    if ST.stringdb_description in src_nodes:
        src_nodes = src_nodes.rename(columns={"stringdb_description": "description"})
        log.debug("Renamed description column!", flush=True)

    compare_columns = [
        identifier
        for identifier in [
            CT.name,
            NT.display_name,
            ST.stringdb_identifier,
            NT.short,
            ST.stringdb_canoncial_name,
            CT.shared_name,
            NT.uniprot,
        ]
        if identifier in src_nodes.columns
    ]
    src_nodes["target_id"] = None
    for identifier in compare_columns:
        if identifier not in ["uniprot"]:
            for col in ["n", ST.stringdb_identifier]:
                not_mapped = src_nodes[src_nodes["target_id"].isna()]
                if not_mapped.empty:
                    break
                collumn_indices = {}
                for i, x in enumerate(target_nodes[col].to_list()):
                    if isinstance(x, list):
                        for y in x:
                            collumn_indices[y] = i
                        continue
                    collumn_indices[x] = i

                mapped = not_mapped[identifier].map(collumn_indices)
                mapped = mapped[mapped.notna()]

                src_nodes.loc[mapped.index, "target_id"] = mapped.copy()

        else:
            # TODO Consider mapping on uniprot but this is not that correct in most cases
            continue
            from ast import literal_eval

            def eval_to_list(x):  # Ugly but did not find any other way to do this
                try:
                    return literal_eval(x)
                except ValueError:
                    return []

            all_uniprots = target_nodes["uniprot"].apply(eval_to_list).apply(pd.Series)
            all_src_uniprots = (
                not_mapped["uniprot"].apply(eval_to_list).apply(pd.Series)
            )
            src_nodes.update(not_mapped)

    src_nodes["target_id"] = src_nodes["target_id"].astype(pd.Int64Dtype())

    src_nodes["c"] = src_nodes.swifter.progress_bar(False).apply(
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

    log.debug(f"Updated {len(src_nodes)} nodes.", flush=True)
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

    # only consider links where start and end are mapped, e.g. nodes which are also in the target network
    node_ids = src_nodes["id"].to_list()

    src_links = src_links[
        src_links[LiT.start].isin(node_ids) & src_links[LiT.end].isin(node_ids)
    ]
    log.debug(f"Considering {len(src_links)} links.", flush=True)
    node_id_map = dict(zip(src_nodes["id"], src_nodes["target_id"]))
    src_links[LiT.start] = src_links[LiT.start].map(node_id_map)
    src_links[LiT.end] = src_links[LiT.end].map(node_id_map)

    log.debug(f"Filtering target links to only consider mapped nodes...", flush=True)

    node_target_ids = src_nodes["target_id"].to_list()
    filter_expr = f"{LiT.start} in @node_target_ids and {LiT.end} in @node_target_ids"
    links_to_consider = target_links.query(filter_expr).copy()

    log.debug(f"Filtered!")

    log.debug(f"Finding index of link in target...", flush=True)

    # def find_link_in_target(x: pd.Series, to_consider: pd.DataFrame) -> int or None:
    #     """Extract the link from the target network that matches with the source links and updated the source link accordingly.

    #     Args:
    #         x (pd.Series): source link
    #         to_consider (pd.DataFrame): DataFrame with all links in which a the start and the end node are mapped.

    #     Returns:
    #         int or None: in case the link is found, the index of the link in the target network is returned. Otherwise None is returned.
    #     """
    #     index = (
    #         to_consider[to_consider[LiT.start] == x[LiT.start] & to_consider[to_consider[LiT.end] == x[LiT.end] | to_consider[to_consider[LiT.start] == x[LiT.end] & to_consider[to_consider[LiT.end] == x[LiT.start]]].index
    #     )
    #     return None
    src_links["link"] = (
        src_links[[LiT.start, LiT.end]]
        .apply(lambda x: "".join(str(y) for y in sorted(x)), axis=1)
        .copy()
    )
    links_to_consider["link"] = (
        links_to_consider[[LiT.start, LiT.end]]
        .apply(lambda x: "".join(str(y) for y in sorted(x)), axis=1)
        .copy()
    )

    merged_df = pd.merge(links_to_consider, src_links, on="link", how="inner")
    duplicate_mask = merged_df["link"].duplicated()
    merged_df = merged_df[~duplicate_mask]
    merged_df = merged_df.drop("link", axis=1)

    new_cols = merged_df[
        [
            c
            for c in merged_df.columns
            if not c.endswith("_x") and c.replace("_y", "") not in target_links.columns
        ]
    ]
    new_cols = new_cols.rename(
        {c: c.replace("_y", "") for c in new_cols.columns}, axis=1
    )
    target_links.update(new_cols)
    # add = src_links[src_links["target_id"].isna()]
    # target_links = pd.concat([target_links, add])
    target_links = target_links.reset_index(drop=True)
    # target_links = Layouter.gen_evidence_layouts(
    #     target_links
    # )  # Transform stringdb scores to evidence values
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
