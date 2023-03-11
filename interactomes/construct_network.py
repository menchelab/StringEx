import json
import os

import networkx as nx
import pandas as pd

import src.settings as st
from interactomes import functional_annotations as fa
from src import map_uniprot
from src.classes import Evidences
from src.classes import LinkTags as LiT
from src.classes import NodeTags as NT, StringTags as ST
from src.classes import Organisms
from src.layouter import Layouter
from interactomes import data_io


def construct_graph(
    networks_directory: str,
    organism: str,
    clean_name: str,
    tax_id: int,
    last_link: int or None = None,
    MAX_NUM_LINKS=st.MAX_NUM_LINKS,
) -> tuple[nx.Graph, dict]:
    """Extracts data from the STRING DB network files and constructs a nx.Graph afterwards.

    Args:
        networks_directory (str): Path to directory where the STRING DB network files are stored for the given organism.
        organism (str): Organism from which the network originates from.
        clean_name (str): Clean name of the organism and final project name.
        tax_id (int): Taxonomy ID of the organism.
        last_link (int o rNone, optional): FOR DEBUGGING: Integer of the last link to be processed. Defaults to None.

    Returns:
        tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
    """
    st.log.debug("Reading raw data...", flush=True)
    (
        link_table,
        alias_table,
        description_table,
        enrichment_table,
    ) = data_io.read_raw_data(networks_directory, tax_id, clean_name, MAX_NUM_LINKS)

    st.log.debug("Generating graph...", flush=True)
    G, links, annotations = gen_graph(
        link_table,
        alias_table,
        description_table,
        enrichment_table,
        organism,
        clean_name,
        networks_directory,
        last_link,
    )
    return G, links, annotations


def gen_graph(
    link_table: pd.DataFrame,
    alias_table: pd.DataFrame,
    description_table: pd.DataFrame,
    enrichment_table: pd.DataFrame,
    organism: str,
    clean_name: str,
    _dir: str,
    last_link: int or None = None,
    threshold: float = 0,
    feature_threshold: int = 0.05,
    annotation_treshold: float = 0.01,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extracts data from the STRING database files and constructs a graph representing the protein-protein interaction network.

    Args:
        network_table (pd.DataFrame): Data Frame containing all links of the network.
        alias_table (pd.DataFrame): Data Frame containing all aliases of the proteins.
        description_table (pd.DataFrame): Data Frame containing Descriptions of the proteins.
        organism (str): Organism from which the network originates from.
        last_link (int or None, optional): FOR DEBUGGING: Integer of the last link to be processed. Defaults to None.
        threshold (int): Score threshold, every edge having an experimental score larger than this value is used for layout calculation. Defaults to 0.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Nodes and link data frames.
    """
    organism_dir = os.path.join(_dir, clean_name)
    species = Organisms.get_scientific_name(organism)
    taxid = Organisms.get_tax_ids(organism)

    if last_link is None:
        last_link = len(link_table)
    else:
        if last_link > len(link_table):
            last_link = len(link_table)

    link_table = link_table.copy()[:last_link]

    link_table[[ev.value for ev in Evidences]] = link_table[
        [ev.value for ev in Evidences]
    ].div(1000)

    st.log.debug("Extracting nodes...", flush=True)
    nodes = pd.DataFrame()
    concat = pd.concat([link_table[LiT.start], link_table[LiT.end]])
    nodes[ST.stringdb_identifier] = concat.unique()
    nodes[NT.species] = species
    st.log.debug("Extracting node label", flush=True)
    nodes[NT.name] = nodes[ST.stringdb_identifier].swifter.apply(
        lambda x: x.split(".")[1]
    )

    functional_annotations = fa.get_annotations(
        _dir,
        clean_name,
        taxid,
        enrichment_table,
    )

    sources = alias_table.groupby("source")
    nodes[NT.uniprot] = None
    for src in sources.groups:
        no_uniprot = nodes[nodes[NT.uniprot].isna()].copy()
        if no_uniprot.empty:
            break
        if "UniProt_AC" in src:
            src = sources.get_group(src)
            no_uniprot[NT.uniprot] = no_uniprot[ST.stringdb_identifier].swifter.apply(
                lambda x: None
                if x not in src.index
                else [src.at[x, "alias"]]
                if isinstance(src.at[x, "alias"], str)
                else [uniprot for uniprot in src.at[x, "alias"]]
            )
            nodes[NT.uniprot].update(no_uniprot[NT.uniprot])
        elif "UniProt_GN" in src:
            src = sources.get_group(src)
            st.log.debug(f"Extracting gene name..", flush=True)
            nodes[NT.gene_name] = nodes[ST.stringdb_identifier].swifter.apply(
                lambda x: src.at[x, "alias"] if x in src.index else None
            )

    no_uniprot = nodes[nodes[NT.uniprot].isna() & nodes[NT.gene_name].notna()]
    nodes = map_gene_names_to_uniprot(nodes, no_uniprot, taxid)

    st.log.debug(f"Extracting description..", flush=True)
    nodes[NT.description] = nodes[ST.stringdb_identifier].swifter.apply(
        lambda x: None
        if x not in description_table.index
        else description_table.at[x, "annotation"].replace(";", " ")
        if description_table.at[x, "annotation"] != "annotation not available"
        else None
    )
    identifiers = dict(zip(nodes[ST.stringdb_identifier], nodes.index))
    link_table[[LiT.start, LiT.end]] = link_table[
        [LiT.start, LiT.end]
    ].swifter.applymap(lambda x: identifiers[x] if x in identifiers else None)
    has_gene_name = nodes[nodes[NT.gene_name].notna()].copy()
    has_gene_name[NT.name] = has_gene_name[NT.gene_name]
    nodes.update(has_gene_name)

    data_io.write_network(
        clean_name,
        nodes,
        link_table,
        functional_annotations,
        # unfiltered_annotations,
        _dir,
    )

    st.log.debug(
        f"Network for {organism} has {len(nodes)} nodes and {len(link_table)} links and has {len(functional_annotations)} functional categories!",
    )

    return nodes, link_table, functional_annotations


def map_gene_names_to_uniprot(
    nodes: pd.DataFrame, missing_annot: dict, taxid: str
) -> nx.Graph:
    """Maps gene names to uniprot ids and adds them to the nodes.

    Args:
        G (nx.Graph): Graph Containing all nodes of the network.
        map_gene_name (dict): dict that maps node ids to gene names.
        taxid (str): taxonomic id of the organism.

    Returns:
        nx.Graph: Same graph as the input graph, but with updated uniprot ids.
    """
    if not missing_annot.empty:
        st.log.debug("Mapping gene names to uniprot ids...", flush=True)
        # invert_map = {v: k for k, v in map_gene_name.items()}

        query_results = map_uniprot.query_gen_names_uniport(
            taxid, list(missing_annot["gene_name"])
        )
        with open("query_results.json", "w") as f:
            json.dump(query_results, f)
        for entry in query_results["results"]:
            gene_name = entry.get("from")
            primaryAccession = None

            if isinstance(entry["to"], dict):
                references = entry["to"].get("uniProtKBCrossReferences")
                for ref in references:
                    if ref.get("database") == "AlphaFoldDB":
                        primaryAccession = ref.get("id")
                        break
                if not primaryAccession:
                    primaryAccession = entry["to"].get("primaryAccession")
            else:
                primaryAccession = entry["to"]
            idx = missing_annot.index[missing_annot["gene_name"] == gene_name]
            nodes.iat[idx, "uniprot"] = primaryAccession

    return nodes


def construct_layouts(
    clean_name: str,
    _dir: str,
    layout_algo: list[str] = None,
    variables: dict = None,
    overwrite: bool = False,
    overwrite_links: bool = False,
    threshold: float = 0.4,
    eps: float = None,
    max_links: int = st.MAX_NUM_LINKS,
    layout_name: list[str] = None,
    max_num_features: int = None,
    functional_threshold: float = 0.1,
    no_layout: bool = False,
    preview_layout: bool = False,
) -> None:
    """Constructs the layouts for the network and compress them into a tar file.

    Args:
        organism (str): Organism which should be processed.
        _dir (str): Path to the directory in which all files are saved in.
        layout_algo (str): Defines the layout algorithm which should be used.
        variables (dict): Defines the variables of the respective layout algorithm.
    """
    functional_lay = False
    for layout in layout_algo:
        if "functional" in layout:
            functional_lay = True

    nodes, all_links, functional_annotations = data_io.read_network(
        _dir, clean_name, functional_lay
    )
    # nodes = nodes.sample(n=5000, random_state=42)

    if functional_lay:
        functional_annotations = dict(
            sorted(
                functional_annotations.items(), key=lambda x: x[1].size, reverse=True
            )[:max_num_features]
        )

    all_links = all_links[:max_links]

    G = nx.from_pandas_edgelist(
        all_links[all_links[Evidences.any.value] > threshold],
        LiT.start,
        LiT.end,
        edge_attr=True,
    )
    layout_graph = G.copy()

    # nx.set_node_attributes(G, nodes.to_dict(orient="index"))
    random_lay = False
    node_data = nodes.T.apply(lambda x: x.dropna().to_dict()).tolist()
    G.add_nodes_from((idx, x) for idx, x in enumerate(node_data) if x is not None)
    layout_graph.add_nodes_from((idx, {}) for idx in nodes.index)

    not_ind = [idx for idx in nodes.index if idx not in G.nodes]
    missing_nodes = nodes.loc[not_ind]
    if len(missing_nodes) > 0:
        G.add_nodes_from(
            (idx, {k: v for k, v in row.items()})
            for idx, row in missing_nodes.iterrows()
        )
    # Map gene names to uniprot ids and add them to the nodes.
    if layout_name is None:
        layout_name = layout_algo
    else:
        for idx, name in enumerate(layout_name):
            if name is None:
                layout_name[idx] = layout_algo[idx]
    tmp = layout_algo.copy()
    tmp_names = layout_name.copy()
    feature_matrices = {}
    categories = []
    filtered_functional_annotations = None
    identifiers = nodes[ST.stringdb_identifier].copy()
    for idx, layout in enumerate(tmp):
        name = tmp_names[idx]
        if "functional" in layout:
            (
                new_algos,
                new_names,
                new_matrices,
                filtered_functional_annotations,
            ) = fa.prepare_feature_matrices(
                name,
                functional_annotations,
                functional_threshold,
                layout,
                identifiers.copy(),
                _dir,
                clean_name,
            )
            for key in new_matrices.keys():
                categories.append(key)
            layout_algo = layout_algo[:idx] + new_algos + layout_algo[idx + 1 :]
            layout_name = layout_name[:idx] + new_names + layout_name[idx + 1 :]
            feature_matrices.update(new_matrices)
        else:
            feature_matrices[name] = None
            categories.append(None)
    for idx, layout in enumerate(tmp):
        file_name = os.path.join(_dir, clean_name, "nodes", f"{layout_name[idx]}.csv")
        if os.path.isfile(file_name) and not overwrite:
            st.log.info(
                f"Node layout for layout {layout_name[idx]} for {clean_name} already exists. Skipping."
            )
            layout_algo.remove(layout)
        else:
            st.log.info(
                f"{file_name} does not exist or overwrite is allowed. Generating layout."
            )
    if no_layout:
        st.log.debug("DEBUG IS ON RANDOM LAYOUT")
        random_lay = True

    layouter = Layouter()
    layouter.graph = layout_graph
    matrix_list = [feature_matrices[name] for name in layout_name]
    layouts = layouter.apply_layout(
        layout_algo, variables, matrix_list, random_lay=random_lay
    )

    st.log.info(f"Generated layouts. Used algorithms: {layout_algo}.")
    data_io.write_link_layouts(clean_name, all_links, _dir, overwrite_links)
    data_io.write_node_layout(
        clean_name,
        nodes,
        layouts,
        _dir,
        eps,
        overwrite=overwrite,
        layout_name=layout_name,
        algos=layout_algo,
        functional_annotations=filtered_functional_annotations,
        feature_matrices=feature_matrices,
        categories=categories,
        preview_layout=preview_layout,
    )
