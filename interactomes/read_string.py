import json
import os
from time import time

import networkx as nx
import numpy as np
import pandas as pd
import swifter
from goatools import obo_parser

import src.settings as st
from interactomes import functional_annotations as fa
from src import map_uniprot
from src.classes import Evidences
from src.classes import LinkTags as LiT
from src.classes import NodeTags as NT
from src.classes import Organisms
from src.layouter import Layouter, visualize_layout
import umap
from matplotlib import pyplot as plt

FUNCTIONAL_CATEGORIES = [
    "Protein Domains (Pfam)",
    "Biological Process (Gene Ontology)",
    "Molecular Function (Gene Ontology)",
    "Annotated Keywords (UniProt)",
    "Cellular Component (Gene Ontology)",
    "Disease-gene associations (DISEASES)",
    "Tissue expression (TISSUES)",
    "Subcellular localization (COMPARTMENTS)",
]


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
    link_table, alias_table, description_table, enrichment_table = read_raw_data(
        networks_directory, tax_id, clean_name, MAX_NUM_LINKS
    )
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
    nodes[NT.identifier] = concat.unique()
    nodes[NT.species] = species
    st.log.debug("Extracting node label", flush=True)
    nodes[NT.name] = nodes[NT.identifier].swifter.apply(lambda x: x.split(".")[1])

    functional_annotations = fa.get_annotations(
        enrichment_table
        # taxid,
        # organism_dir,
        # nodes.size,
    )

    sources = alias_table.groupby("source")
    nodes[NT.uniprot] = None
    for src in sources.groups:
        no_uniprot = nodes[nodes[NT.uniprot].isna()].copy()
        if no_uniprot.empty:
            break
        if "UniProt_AC" in src:
            src = sources.get_group(src)
            no_uniprot[NT.uniprot] = no_uniprot[NT.identifier].swifter.apply(
                lambda x: None
                if x not in src.index
                else src.at[x, "alias"]
                if isinstance(src.at[x, "alias"], str)
                else [uniprot for uniprot in src.at[x, "alias"]]
            )
            nodes[NT.uniprot].update(no_uniprot[NT.uniprot])
        elif "UniProt_GN" in src:
            src = sources.get_group(src)
            st.log.debug(f"Extracting gene name..", flush=True)
            nodes[NT.gene_name] = nodes[NT.identifier].swifter.apply(
                lambda x: src.at[x, "alias"] if x in src.index else None
            )

    no_uniprot = nodes[nodes[NT.uniprot].isna() & nodes[NT.gene_name].notna()]
    nodes = map_gene_names_to_uniprot(nodes, no_uniprot, taxid)

    st.log.debug(f"Extracting description..", flush=True)
    nodes[NT.description] = nodes[NT.identifier].swifter.apply(
        lambda x: None
        if x not in description_table.index
        else description_table.at[x, "annotation"].replace(";", " ")
        if description_table.at[x, "annotation"] != "annotation not available"
        else None
    )
    identifiers = dict(zip(nodes[NT.identifier], nodes.index))
    link_table[[LiT.start, LiT.end]] = link_table[
        [LiT.start, LiT.end]
    ].swifter.applymap(lambda x: identifiers[x] if x in identifiers else None)
    has_gene_name = nodes[nodes[NT.gene_name].notna()].copy()
    has_gene_name[NT.name] = has_gene_name[NT.gene_name]
    nodes.update(has_gene_name)

    write_network(
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
    t1 = time()
    nodes.to_pickle(f"{path}/nodes.pickle")
    processed_network.to_pickle(f"{path}/links.pickle")
    os.makedirs(f"{path}/functional_annotations", exist_ok=True)

    # for key, value in functional_annotations.items():
    #     value.to_pickle(f"{path}/functional_annotations/{key}_filtered.pickle")

    # for key, value in unfiltered_annotations.items():
    #     value.to_pickle(f"{path}/functional_annotations/{key}.pickle")

    for key, value in functional_annotations.items():
        value.to_pickle(f"{path}/functional_annotations/{key}.pickle")

    st.log.debug(f"Writing pickle data took {time() - t1} seconds.", flush=True)


def construct_layouts(
    organism: str,
    _dir: str,
    layout_algo: list[str] = None,
    variables: dict = None,
    overwrite: bool = False,
    overwrite_links: bool = False,
    threshold: float = 0.4,
    max_links: int = st.MAX_NUM_LINKS,
    layout_name: list[str] = None,
    max_num_features: int = None,
    functional_threshold: float = 0.05,
    debug: bool = False,
) -> None:
    """Constructs the layouts for the network and compress them into a tar file.

    Args:
        organism (str): Organism which should be processed.
        _dir (str): Path to the directory in which all files are saved in.
        layout_algo (str): Defines the layout algorithm which should be used.
        variables (dict): Defines the variables of the respective layout algorithm.
    """

    def gen_layout(
        G: nx.Graph,
        layout_algo: list[str] = None,
        variables: dict = None,
        feature_matrices: list[pd.DataFrame] = None,
        random_lay=False,
    ) -> dict:
        """Generates a 3D layout for the graph.

        Args:
            G (nx.Graph): Graph to generate layout for.

        Returns:
            dict: Dictionary with node ids as keys and 3D positions as values.
        """
        layouter = Layouter()
        layouter.graph = G
        layouts = layouter.apply_layout(
            layout_algo, variables, feature_matrices, random_lay=random_lay
        )
        # for algo, layout in layouts.items():
        #     layout = np.array(list(layout.values()))
        #     pos = Layouter.normalize_pos(layout)
        #     layouts[algo] = pos
        return layouts

    def write_node_layout(
        organism: str,
        nodes: pd.DataFrame,
        layouts: dict,
        _dir: str,
        overwrite: bool = False,
        layout_name: str = None,
        algos: list[str] = None,
        functional_annotations: dict = None,
        feature_matrices: list[pd.DataFrame] = None,
        categories: list[str] = None,
    ) -> None:
        """Will write the node layout to a csv file with the following format:
        x,y,r,g,b,a,name;uniprot_id;description. File name is: {organism}_node.csv located in projects folder.

        Args:
            organism (str): organism from which the network originates from.
            G (nx.Graph): Graph of the network.
            layout (dict): calculated layout of the graph. With the node id as key and the position as value.
        """
        _directory = os.path.join(_dir, organism, "nodes")
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
            if categories:
                category = categories[idx]
                st.log.debug(category)
            layout_nodes = nodes.copy()
            layout_nodes["x"] = pos[:, 0]
            layout_nodes["y"] = pos[:, 1]
            layout_nodes["z"] = pos[:, 2]
            if layout_name and len(layout_name) >= idx:
                name = layout_name[idx]
            st.log.debug(f"Writing node layout for {name} for {organism}.")
            if feature_matrices and feature_matrices[idx] is not None:
                feature_matrix = feature_matrices[idx].copy()
            # TODO: Change this with the real layout name to the name provided by the user, makes to much problems with the current implementation
            colors = pd.Series(
                [[1, 1, 1] for _ in range(len(layout_nodes))], index=layout_nodes.index
            )
            if "functional" in algo and category in functional_annotations:
                layout_nodes["features"] = feature_matrix.any(axis=1)
                has_features = layout_nodes["features"]

                category = functional_annotations[category].copy()

                st.log.debug("Adding colors to functional clusters..")
                to_color = colors[has_features].apply(lambda x: None).copy()

                used_colors = set()
                feature_matrix = feature_matrix[has_features]
                # clusterable_embedding = umap.UMAP(
                #     n_neighbors=10,
                #     min_dist=0.9,
                # ).fit_transform(feature_matrix.values)
                # plt.scatter(
                #     clusterable_embedding[:, 0],
                #     clusterable_embedding[:, 1],
                #     cmap="Spectral",
                # )
                # plt.show()
                for term_idx, _ in category.iterrows():
                    # check if any coloring necessary
                    needs_color = to_color.isna()
                    if not needs_color.any():
                        st.log.debug("All colors are set...")
                        break

                    term_data = feature_matrix[term_idx]
                    if not term_data.any():
                        continue

                    color, used_colors = get_color(used_colors)

                    highlight = term_data.swifter.progress_bar(False).apply(
                        lambda x: color if x else None,
                    )
                    has_new_color = ~highlight.isna()
                    to_multiply = np.logical_and(~needs_color, has_new_color)
                    if np.any(to_multiply):
                        to_color[to_multiply] *= highlight[to_multiply]
                    to_add = has_new_color & needs_color
                    if np.any(to_add):
                        to_color[to_add] = highlight[to_add]

                colors.update(to_color)

            colors = np.array(colors.tolist())
            # for i in range(3):
            #     st.log.debug(f"{colors[:, i].min()}, {colors[:, i].max()}")
            colors = 0.5 - np.abs(colors - 0.5) + 0.5
            # visualize_layout(
            #     layout_nodes[["x", "y", "z"]].to_numpy(),
            #     colors,
            # )
            # continue
            colors *= 255
            colors = colors.astype(int)
            layout_nodes[["r", "g", "b"]] = colors
            layout_nodes["a"] = 255 // 4
            file_name = os.path.join(_directory, f"{name}.csv")
            if os.path.isfile(file_name) and not overwrite:
                st.log.info(
                    f"Node layout for {name} for {organism} already exists. Skipping."
                )
                continue
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

            all_links[ev] = all_links[ev].apply(
                get_link_colors, args=(color_scheme[ev],)
            )

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

    functional_lay = False
    for layout in layout_algo:
        if "functional" in layout:
            functional_lay = True

    nodes, all_links, functional_annotations = read_network(
        organism, _dir, functional_lay
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
    feature_matrices = []
    categories = None
    filtered_functional_annotations = None
    identifiers = nodes[NT.identifier].copy()
    for idx, layout in enumerate(tmp):
        if "functional" in layout:
            name = tmp_names[idx]
            (
                new_algos,
                new_names,
                new_matrices,
                filtered_functional_annotations,
                categories,
            ) = prepare_feature_matrices(
                name,
                functional_annotations,
                functional_threshold,
                layout,
                identifiers.copy(),
            )
            layout_algo = layout_algo[:idx] + new_algos + layout_algo[idx + 1 :]
            layout_name = layout_name[:idx] + new_names + layout_name[idx + 1 :]
            feature_matrices = (
                feature_matrices[:idx] + new_matrices + feature_matrices[idx + 1 :]
            )
        else:
            feature_matrices.append(None)
    for idx, layout in enumerate(tmp):
        file_name = os.path.join(_dir, organism, "nodes", f"{layout_name[idx]}.csv")
        if os.path.isfile(file_name) and not overwrite:
            st.log.info(
                f"Node layout for layout {layout_name[idx]} for {organism} already exists. Skipping."
            )
            layout_algo.remove(layout)
        else:
            st.log.info(
                f"{file_name} does not exist or overwrite is allowed. Generating layout."
            )
    if debug:
        st.log.debug("DEBUG IS ON RANDOM LAYOUT")
        random_lay = True
    layouts = gen_layout(
        layout_graph, layout_algo, variables, feature_matrices, random_lay
    )
    st.log.info(f"Generated layouts. Used algorithms: {layout_algo}.")
    write_link_layouts(organism, all_links, _dir, overwrite_links)
    write_node_layout(
        organism,
        nodes,
        layouts,
        _dir,
        overwrite=overwrite,
        layout_name=layout_name,
        algos=layout_algo,
        functional_annotations=filtered_functional_annotations,
        feature_matrices=feature_matrices,
        categories=categories,
    )


def read_raw_data(
    networks_directory: str, tax_id: str, clean_name: str, MAX_NUM_LINKS: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    directory = os.path.join(networks_directory, clean_name)

    link_file = os.path.join(directory, f"{tax_id}.protein.links.detailed.v11.5.txt.gz")

    filtered = os.path.join(
        directory, f"{tax_id}.protein.links.detailed.v11.5.filtered.txt.gz"
    )

    # if os.path.isfile(filtered):
    #     link_file = filtered

    alias_file = os.path.join(directory, f"{tax_id}.protein.aliases.v11.5.txt.gz")
    description_file = os.path.join(directory, f"{tax_id}.protein.info.v11.5.txt.gz")
    enrichment_file = os.path.join(
        directory, f"{tax_id}.protein.enrichment.terms.v11.5.txt.gz"
    )
    # annot_file = os.path.join(directory, f"{tax_id}.gaf.gz")
    # ont_file = os.path.join(directory, "..", "go-basic.obo")

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
    description_table = pd.read_table(description_file, header=0, sep="\t", index_col=0)

    enrichment_file = pd.read_table(enrichment_file, header=0, sep="\t")

    return link_table, alias_table, description_table, enrichment_file


def prepare_feature_matrices(
    name,
    functional_annotations,
    functional_threshold,
    layout,
    identifiers,
    functional_categories=FUNCTIONAL_CATEGORIES,
):
    new_algos = []
    new_names = []
    new_matrices = []
    filtered_functional_annotations = {}
    categories = []
    for cat in functional_annotations:
        category = functional_annotations[cat].copy()
        category = category[category["number_of_members"] > functional_threshold]
        if category.empty:
            continue
        if cat not in functional_categories:
            st.log.debug(
                f"Category {cat} is not a valid functional category. Consider adding it as its seems to be relevant."
            )
            continue
        n = f"{name}{cat}"
        new_algos.append(layout)
        new_names.append(n)
        st.log.debug(f"Mapping terms of category {cat} to nodes...", flush=True)
        feature_matrix = category.swifter.apply(
            lambda x: identifiers.isin(x.members), axis=1
        ).T
        new_matrices.append(feature_matrix)
        filtered_functional_annotations[cat] = category
        categories.append(cat)

    return (
        new_algos,
        new_names,
        new_matrices,
        filtered_functional_annotations,
        categories,
    )


def read_network(
    organism: str, _dir: str, read_functional: bool
) -> tuple[nx.Graph, dict]:
    """Reads the graphml of the network and a json file with the link layouts.

    Args:
        organism (str): Organism from which the network originates from.

    Returns:
        tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
    """
    t1 = time()
    path = os.path.join(_dir, organism)
    nodes = pd.read_pickle(f"{path}/nodes.pickle")
    all_links = pd.read_pickle(f"{path}/links.pickle")

    functional_annotations = None
    if read_functional:
        functional_annotations = {}
        for file in os.listdir(f"{path}/functional_annotations"):
            if not file.endswith(".pickle"):
                continue

            if file.endswith(".pickle"):
                functional_annotations[file.strip(".pickle")] = pd.read_pickle(
                    f"{path}/functional_annotations/{file}"
                )
    all_links = all_links.replace("", pd.NA)
    st.log.debug(f"Loading data from pickles took {time() - t1} seconds.", flush=True)

    return nodes, all_links, functional_annotations


def get_color(used_colors: set):
    while True:
        color = np.random.randint(0, 255, 3)
        hex = "#{:02x}{:02x}{:02x}".format(*color)
        if hex not in used_colors:
            used_colors.add(hex)
            return color / 255, used_colors
