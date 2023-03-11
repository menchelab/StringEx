import pandas as pd
import numpy as np
import os
from src.classes import NodeTags as NT
import src.settings as st
from src.classes import Evidences, Organisms
from src.classes import LinkTags as LiT
from src.classes import StringTags as ST
import time
import networkx as nx
from goatools import obo_parser
from interactomes import util
import pickle


def write_node_layout(
    organism: str,
    nodes: pd.DataFrame,
    layouts: dict,
    _dir: str,
    eps: float = None,
    overwrite: bool = False,
    layout_name: str = None,
    algos: list[str] = None,
    functional_annotations: dict = None,
    feature_matrices: dict[str, pd.DataFrame] = None,
    categories: list[str] = None,
    preview_layout: bool = False,
) -> None:
    """Will write the node layout to a csv file with the following format:
    x,y,r,g,b,a,name;uniprot_id;description. File name is: {organism}_node.csv located in projects folder.

    Args:
        organism (str): organism from which the network originates from.
        G (nx.Graph): Graph of the network.
        layout (dict): calculated layout of the graph. With the node id as key and the position as value.
    """
    _directory = os.path.join(_dir, organism)
    os.makedirs(_directory, exist_ok=True)
    nodes["a"] = 255 // 4
    nodes = nodes.sort_index()

    has_gene_name = nodes["gene_name"].notna()
    nodes["ensembl"] = nodes[NT.name].copy()
    nodes.loc[has_gene_name, NT.name] = nodes.loc[has_gene_name, "gene_name"]
    nodes["attr"] = nodes.apply(
        lambda x: f"{x.get(NT.name)};{x.get(NT.uniprot)};{x.get(NT.description)};{x.get('ensembl')}",
        axis=1,
    )
    for idx, layout in layouts.items():
        pos = np.array(list(layout.values()))
        name = layout_name[idx]
        algo = algos[idx]
        category = None
        if categories:
            category = categories[idx]

        layout_nodes = nodes.copy()
        layout_nodes["x"] = pos[:, 0]
        layout_nodes["y"] = pos[:, 1]
        layout_nodes["z"] = pos[:, 2]
        if layout_name and len(layout_name) >= idx:
            name = layout_name[idx]
        st.log.debug(f"Writing node layout for {name} for {organism}.")

        feature_matrix = None
        if feature_matrices and feature_matrices[name] is not None:
            feature_matrix = feature_matrices[name].copy()

        if functional_annotations is not None:
            category = functional_annotations.get(category, None)

        cluster_colors = util.color_layout(
            len(layout_nodes),
            algo,
            category,
            feature_matrix,
            eps=eps,
            pos=pos,
            preview_layout=preview_layout,
        )
        layout_nodes[["r", "g", "b", "a"]] = cluster_colors[["r", "g", "b", "a"]]
        write_node_csv(_directory, organism, name, layout_nodes, overwrite)
        if "functional" in algo and category is not None:
            cluster = pd.concat(
                [layout_nodes[ST.stringdb_identifier], cluster_colors["cluster"]],
                axis=1,
            )
            write_cluster_information(_directory, organism, name, cluster, overwrite)


def write_cluster_information(_directory, organism, name, cluster, overwrite):
    cluster_dir = os.path.join(_directory, "clusters")
    file_name = os.path.join(cluster_dir, f"{name}_cluster.csv")
    tax_id = Organisms.get_tax_ids(organism=organism)
    cluster = util.get_cluster_labels(cluster, tax_id, cluster_dir, name)
    os.makedirs(cluster_dir, exist_ok=True)
    # cluster = cluster.apply(lambda x: ",".join(x["n"]))
    if os.path.isfile(file_name) and not overwrite:
        st.log.info(f"Node layout for {name} for {organism} already exists. Skipping.")
        return
    cluster.to_csv(file_name, sep="\t", header=True, index=True)
    st.log.info(f"Node layout for {organism} has been written to {file_name}.")


def read_cluster_information(_directory, name):
    _directory = os.path.join(_directory, "clusters")
    file_name = os.path.join(_directory, f"{name}_cluster.csv")
    if not os.path.isfile(file_name):
        return None
    cluster = pd.read_csv(file_name, sep="\t", header=0, index_col=0)
    return cluster


def write_node_csv(_directory, organism, name, layout_nodes, overwrite):
    _directory = os.path.join(_directory, "nodes")
    file_name = os.path.join(_directory, f"{name}.csv")
    os.makedirs(_directory, exist_ok=True)
    if os.path.isfile(file_name) and not overwrite:
        st.log.info(f"Node layout for {name} for {organism} already exists. Skipping.")
        return
    layout_nodes[["x", "y", "z", "r", "g", "b", "a", "attr"]].to_csv(
        file_name, sep=",", header=False, index=None
    )
    st.log.info(f"Node layout for {organism} has been written to {file_name}.")


def write_link_layouts(
    organism: str,
    all_links: pd.DataFrame,
    _dir: str,
    overwrite: bool = False,
) -> None:
    """Will write the link layouts to a csv file with the following format:
    start,end,r,g,b,a. File name is: {organism}_{ev}.csv located in projects folder.

    Args:
        organism (str): Organism from which the network originates from.
        l_lays (dict): Dictionary of link layouts with ev as key and list of links as value.
        all_links (list): contains all links in the network, predicted and experimental proven.
        dir (str): Directory to write the files to.
    """
    color_scheme = Evidences.get_default_scheme()
    _directory = os.path.join(_dir, organism, "links")
    os.makedirs(_directory, exist_ok=True)
    for ev in color_scheme:
        file_name = os.path.join(_directory, f"{ev}.csv")
        if os.path.isfile(file_name) and not overwrite:
            st.log.info(
                f"link layout for evidence {ev} for {organism} already exists. Skipping."
            )
            continue

        def get_link_colors(x, color):
            return color[:3] + tuple((int(color[3] * x),))

        all_links[ev] = all_links[ev].apply(get_link_colors, args=(color_scheme[ev],))

        ev_text = all_links[all_links[ev].apply(lambda x: x[3] > 0)]
        ev_text = ev_text[[ev, LiT.start, LiT.end]]
        if not ev_text.empty:
            ev_text["r"] = ev_text[ev].apply(lambda x: x[0])
            ev_text["g"] = ev_text[ev].apply(lambda x: x[1])
            ev_text["b"] = ev_text[ev].apply(lambda x: x[2])
            ev_text["a"] = ev_text[ev].apply(lambda x: x[3])
        ev_text = ev_text.drop(columns=ev)
        ev_text.to_csv(file_name, index=False, header=False)
        st.log.info(
            f"link layout for evidence {ev} for {organism} has been written to {file_name}."
        )


def write_network(
    organism: str,
    nodes: pd.DataFrame,
    processed_network: pd.DataFrame,
    functional_annotations: dict,
    # unfiltered_annotations: dict,
    _dir: str,
) -> None:
    """Write the graph to a json file. And write the l_lays to a json file.

    Args:
        organism (str): Organism from which the network originates from.
        G (nx.Graph): Graph of the network.
        l_lays (dict): Link layouts with ev as key and list of links as value.
    """
    path = os.path.join(_dir, organism)
    os.makedirs(path, exist_ok=True)
    t1 = time.time()
    nodes.to_pickle(f"{path}/nodes.pickle")
    processed_network.to_pickle(f"{path}/links.pickle")
    os.makedirs(f"{path}/functional_annotations", exist_ok=True)

    write_functional_annotations(path, functional_annotations)

    st.log.debug(f"Writing pickle data took {time.time() - t1} seconds.", flush=True)


def read_network(
    _dir: str, organism: str, read_functional: bool
) -> tuple[nx.Graph, dict]:
    """Reads the graphml of the network and a json file with the link layouts.

    Args:
        _dir (str): Directory where the interactomes are stored.
        organism (str): Organism from which the network originates from.
        read_functional (bool): Whether to read the functional annotations or not.

    Returns:
        tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
    """
    t1 = time.time()
    nodes = read_nodes_pickle(_dir, organism)
    all_links = read_links_pickle(_dir, organism)

    functional_annotations = None
    if read_functional:
        functional_annotations = read_functional_annotations(_dir, organism)

    all_links = all_links.replace("", pd.NA)
    st.log.debug(
        f"Loading data from pickles took {time.time() - t1} seconds.", flush=True
    )

    return nodes, all_links, functional_annotations


def read_links_pickle(_dir, organism):
    path = os.path.join(_dir, organism)
    return pd.read_pickle(f"{path}/links.pickle")


def read_nodes_pickle(_dir, organism):
    path = os.path.join(_dir, organism)
    return pd.read_pickle(f"{path}/nodes.pickle")


def read_raw_data(
    networks_directory: str, tax_id: str, clean_name: str, MAX_NUM_LINKS: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    directory = os.path.join(networks_directory, clean_name)
    link_table = read_links(directory, tax_id, MAX_NUM_LINKS)
    alias_table = read_aliases(directory, tax_id)
    description_table = read_descriptions(directory, tax_id)
    enrichment_table = read_enrichment_terms(directory, tax_id)

    # if os.path.isfile(filtered):
    #     link_file = filtered

    return link_table, alias_table, description_table, enrichment_table


def read_go_annotation(annot_file, ont_file):
    """Reads the annotation file and returns a dictionary with the annotations."""
    annot = pd.read_table(
        annot_file, comment="!", header=None, sep="\t", low_memory=False
    )
    annot = annot.drop(columns=[0, 7, 11, 12, 13, 14, 15, 16])
    annot.columns = [
        NT.uniprot,
        NT.gene_name,
        "qualifier",
        "go",
        "db_reference",
        "evidence",
        "aspect",
        "name",
        "synonym",
    ]
    annot.index = annot[NT.gene_name]
    annot = annot.drop(columns=[NT.gene_name])
    ont = obo_parser.GODag(ont_file)
    return annot, ont


def read_enrichment_terms(directory, tax_id):
    enrichment_file = os.path.join(
        directory, f"{tax_id}.protein.enrichment.terms.v11.5.txt.gz"
    )
    enrichment_table = pd.read_table(enrichment_file, header=0, sep="\t")
    return enrichment_table


def read_descriptions(directory, tax_id):
    description_file = os.path.join(directory, f"{tax_id}.protein.info.v11.5.txt.gz")
    description_table = pd.read_table(description_file, header=0, sep="\t", index_col=0)
    return description_table


def read_aliases(directory, tax_id):
    alias_file = os.path.join(directory, f"{tax_id}.protein.aliases.v11.5.txt.gz")
    alias_table = pd.read_table(
        alias_file,
        sep="\t",
        header=0,
        index_col=0,
    )
    # Filter out every entry which does not contains these three sources
    alias_table = alias_table.loc[
        alias_table["source"].isin(
            [
                "Ensembl_UniProt_AC",
                "BLAST_UniProt_AC",
                "BLAST_UniProt_GN_Name",
                "Ensembl_UniProt_GN_Name",
            ]
        )
    ]
    return alias_table


def read_links(directory, tax_id, MAX_NUM_LINKS):
    """Reads the links file and returns a dictionary with the links."""
    link_file = os.path.join(directory, f"{tax_id}.protein.links.detailed.v11.5.txt.gz")

    filtered = os.path.join(
        directory, f"{tax_id}.protein.links.detailed.v11.5.filtered.txt.gz"
    )

    rename_dict = {
        "protein1": LiT.start,
        "protein2": LiT.end,
        "neighborhood": Evidences.stringdb_neighborhood.value,
        "fusion": Evidences.stringdb_fusion.value,
        "cooccurence": Evidences.stringdb_cooccurrence.value,
        "coexpression": Evidences.stringdb_coexpression.value,
        "experimental": Evidences.stringdb_experiments.value,
        "database": Evidences.stringdb_databases.value,
        "textmining": Evidences.stringdb_textmining.value,
        "combined_score": Evidences.any.value,
        "homology": Evidences.stringdb_similarity.value,
    }
    type_dict = {
        LiT.start: str,
        LiT.end: str,
        Evidences.stringdb_neighborhood.value: np.int64,
        Evidences.stringdb_fusion.value: np.int64,
        Evidences.stringdb_cooccurrence.value: np.int64,
        Evidences.stringdb_coexpression.value: np.int64,
        Evidences.stringdb_experiments.value: np.int64,
        Evidences.stringdb_databases.value: np.int64,
        Evidences.stringdb_textmining.value: np.int64,
        Evidences.any.value: np.int64,
        Evidences.stringdb_similarity.value: np.int64,
    }

    link_table = pd.read_table(link_file, header=0, sep=" ")
    for default_col, new_col in rename_dict.items():
        if default_col in link_table.columns:
            link_table = link_table.rename(columns={default_col: new_col})
        elif new_col not in link_table.columns:
            link_table[new_col] = [0 for _ in range(len(link_table))]
    link_table = link_table.astype(type_dict)

    n = len(link_table)
    if n > MAX_NUM_LINKS:
        st.log.debug(f"Too many links. Will filter them.", flush=True)
        link_table = link_table.sort_values(
            [Evidences.stringdb_experiments.value, Evidences.any.value], ascending=False
        )
        st.log.debug(
            "Sorted link list first based on experimental value and secondly on total score.",
            flush=True,
        )
        link_table = link_table[
            link_table[LiT.start].notna() & link_table[LiT.end].notna()
        ]
        st.log.debug("Dropped links where start or end is NA.", flush=True)

        link_table = link_table.reset_index(drop=True)

        link_table = link_table.truncate(after=MAX_NUM_LINKS - 1)
        link_table.to_csv(filtered, compression="gzip", sep=" ", index=False)
    st.log.debug("Filtered and sorted...", flush=True)

    return link_table


def read_uniprot_keywords(keywords_file):
    """Reads the keywords file and returns a dictionary with the keywords."""
    keywords = pd.read_table(keywords_file, header=0, index_col=0, sep="\t")
    return keywords


def read_node_layouts(_dir: str, clean_name: str) -> dict[str, pd.DataFrame]:
    _directory = os.path.join(_dir, clean_name, "nodes")
    layouts = {}
    for file in os.listdir(_directory):
        if not file.endswith(".csv"):
            continue
        file_path = os.path.join(_directory, file)
        layout_name = file.strip(".csv")
        data = pd.read_csv(
            file_path,
            sep=",",
            header=None,
            names=["x", "y", "z", "r", "g", "b", "a", "attr"],
        )
        layouts[layout_name] = data
    return layouts


def read_link_layouts(_dir: str, clean_name: str) -> dict[str, pd.DataFrame]:
    _directory = os.path.join(_dir, clean_name, "links")
    layouts = {
        file.strip(".csv"): pd.read_csv(file)
        for file in os.listdir(_directory)
        if file.endswith(".csv")
    }
    return layouts


def write_functional_annotations(_dir, functional_annotations):
    """Writes the functional annotations to a csv file.

    Args:
        _dir (str): Path to the directory in which all files are saved in.
        organism (str): Organism which should be processed.
        functional_annotations (dict): Dictionary containing the functional annotations.
    """
    os.makedirs(os.path.join(_dir, "functional_annotations"), exist_ok=True)
    for feature, annotations in functional_annotations.items():
        file_name = os.path.join(_dir, "functional_annotations", f"{feature}.pickle")
        annotations.to_pickle(file_name)


def read_functional_annotations(_dir, organism):
    """Reads the functional annotations from a csv file.

    Args:
        _dir (str): Path to organism directory.
    Returns:
        dict: Dictionary containing the functional annotations.
    """
    path = os.path.join(_dir, organism, "functional_annotations")
    functional_annotations = {}
    for file in os.listdir(path):
        if not file.endswith(".pickle"):
            continue

        if file.endswith(".pickle"):
            functional_annotations[file.strip(".pickle")] = pd.read_pickle(
                os.path.join(path, file)
            )
    return functional_annotations


def write_feature_matrices(
    _dir: str,
    organism: str,
    feature_matrices: dict[str, pd.DataFrame],
):
    """Construct feature matrices for all proteins in STRING."""
    path = os.path.join(_dir, organism, "functional_annotations", "fm")
    os.makedirs(path, exist_ok=True)
    for name, feature_matrix in feature_matrices.items():
        feature_matrix["annotations"] = feature_matrix.sum(axis=1)
        with open(os.path.join(path, f"{name}.pickle"), "wb") as f:
            pickle.dump(feature_matrix, f)
    return feature_matrices


def read_feature_matrices(
    _dir: str, organism: str, n: int, functional_threshold: float = 0.1
):
    """Read feature matrices from disk."""
    feature_matrices = {}
    for fm in os.listdir(os.path.join(_dir, organism, "functional_annotations", "fm")):
        if fm.endswith(".pickle"):
            category = fm.strip(".pickle")
            file_path = os.path.join(_dir, organism, "functional_annotations", "fm", fm)
            # Here to have min_threshold attribute
            fm = pd.read_pickle(file_path)
            if functional_threshold < 0.01:
                st.log.debug(
                    "The feature matrices are only calculated for a threshold => 0.1. For lower values the resulting matrices are to sparse"
                )
                exit()
            fm = fm.T
            fm_arr = fm.to_numpy()
            row_sums = np.sum(fm_arr, axis=1)
            mask = row_sums / n > functional_threshold
            fm_filtered = fm_arr[mask, :]
            fm = pd.DataFrame(fm_filtered, index=fm.index[mask], columns=fm.columns).T
            feature_matrices[category] = fm

    return feature_matrices


if __name__ == "__main__":
    pass
