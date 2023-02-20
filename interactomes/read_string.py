import json
import os
from time import time

import networkx as nx
import numpy as np
import pandas as pd
import swifter
from goatools import obo_parser

import src.settings as st
from src import map_uniprot
from src.classes import Evidences
from src.classes import LinkTags as LiT
from src.classes import NodeTags as NT
from src.classes import Organisms
from src.layouter import Layouter


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
    link_table, alias_table, description_table, annot_table, ont = read_raw_data(
        networks_directory, tax_id, clean_name, MAX_NUM_LINKS
    )
    st.log.debug("Generating graph...", flush=True)
    G, links = gen_graph(
        link_table,
        alias_table,
        description_table,
        annot_table,
        ont,
        organism,
        clean_name,
        networks_directory,
        last_link,
    )
    return G, links


def extract_nodes(
    # idx: int,
    # identifier: str,
    node: pd.Series,
    alias_table: pd.DataFrame,
    description_table: pd.DataFrame,
    ont_table: pd.DataFrame,
) -> pd.Series:
    """Extract nodes from the STRING DB network files.

    Args:
        node (pd.Series): Row of the nodes DataFrame.
        alias_table (pd.DataFrame): DataFrame containing all aliases for all nodes.
        description_table (pd.DataFrame): DataFrame containing all descriptions for all nodes.

    Returns:
        pd.Series: Updated node with aliases.
    """

    def extract_uniprot_id(alias: pd.DataFrame) -> list:
        """Extracts possible uniprot ids from the alias column of a node.

        Args:
            alias (pd.DataFrame): Dataframe containing only data for a single node.

        Returns:
            list: contains all uniprot ids for a node.
        """
        for tag in ["Ensembl_UniProt_AC", "BLAST_UniProt_AC"]:
            row = alias["source"] == tag
            if isinstance(row, bool):
                continue

            row = alias.loc[alias["source"] == tag]
            if row.empty:
                continue
            uniprot = list(alias.loc[alias["source"] == tag].get("alias"))
            if len(uniprot) > 0:
                return uniprot[0]
        return None

    def extract_gene_name(alias: pd.DataFrame):
        """Extracts possible gene names from the alias column of a node.

        Args:
            alias (pd.DataFrame): Dataframe containing only data for a single node.

        Returns:
            list: contains all gene names for a node.
        """
        row = alias["source"] == "BLAST_UniProt_GN_Name"
        if isinstance(row, bool):
            return None
        gene_name = list(
            alias.loc[alias["source"] == "BLAST_UniProt_GN_Name"].get("alias")
        )
        if len(gene_name) == 0:
            return None

        return gene_name[0]

    def extract_go_terms(
        ont_table: pd.DataFrame, node: pd.Series, identifier: str, column: str
    ) -> pd.Series:
        """Extracts GO terms from the ontology table.

        Args:
            ont_table (pd.DataFrame): Data Frame containing all ontology terms.
            node (pd.Series): Node to be updated.
            identifier (str): Identifier of the node.
            column (str): Column to search for the identifier.

        Returns:
            pd.Series: Updated Node
        """
        rows = ont_table[ont_table[column] == identifier]
        for entry in rows.itertuples():
            qualifier = entry.qualifier
            if entry.go not in node:
                node[entry.go] = qualifier
        # ont_table = ont_table.drop(index=rows.index)
        return node  # , ont_table

    # get uniprot id(s)
    identifier = node[NT.name]
    node[NT.name] = node[NT.name].split(".")[1]
    alias = alias_table[alias_table.index == identifier]
    if not alias.empty:
        # alias_table = alias_table.drop(index=alias.index)
        uniprot = extract_uniprot_id(alias)
        if uniprot:
            # node, ont_table = extract_go_terms(ont_table, node, uniprot, "id")
            node = extract_go_terms(ont_table, node, uniprot, "id")
    else:
        uniprot = None
    node["uniprot"] = uniprot

    gene_name = extract_gene_name(alias)
    if gene_name:
        node["gene_name"] = gene_name
        # node, ont_table = extract_go_terms(ont_table, node, gene_name, "symbol")
        node = extract_go_terms(ont_table, node, gene_name, "symbol")

    else:
        node["gene_name"] = None

    # node[NT.species] = species
    annotation = description_table.at[identifier, "annotation"]

    if annotation != "annotation not available":
        node[NT.description] = annotation.replace(";", "")
        # description_table = description_table.drop(index=identifier)

    return node  # , alias_table, description_table, ont_table


def gen_graph(
    link_table: pd.DataFrame,
    alias_table: pd.DataFrame,
    description_table: pd.DataFrame,
    annot_table: pd.DataFrame,
    ont: obo_parser.GODag,
    organism: str,
    clean_name: str,
    _dir: str,
    last_link: int or None = None,
    threshold: int = 0,
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
    nodes[NT.name] = concat.unique()
    nodes[NT.species] = species

    nodes = nodes.swifter.apply(
        extract_nodes, axis=1, args=(alias_table, description_table, annot_table)
    )
    st.log.debug("Nodes extracted!", flush=True)

    def get_short(x):
        splitted = x.split(".")
        if len(splitted) > 1:
            return splitted[1]
        return x

    st.log.debug("Preparing short names...", flush=True)
    link_table[LiT.start] = link_table[LiT.start].swifter.apply(get_short)
    link_table[LiT.end] = link_table[LiT.end].swifter.apply(get_short)

    st.log.debug("Setting link ids...", flush=True)
    #     return link

    names = nodes[NT.name].tolist()
    link_table[[LiT.start, LiT.end]] = link_table[
        [LiT.start, LiT.end]
    ].swifter.applymap(lambda x: names.index(x) if x in names else None)

    st.log.debug("Mapped updated link start and end to node indices!", flush=True)

    no_uniprot = nodes[nodes["uniprot"].isna() & nodes["gene_name"].notna()]
    nodes = map_gene_names_to_uniprot(nodes, no_uniprot, taxid)
    # go_terms = pd.DataFrame([{"col": s} for s in nodes["go"]])
    # nodes = nodes.drop(columns=["go"])

    # features = Layouter.get_feature_matrix(go_terms, 20)
    features = [c for c in nodes.columns if "GO:" in c]

    new_names = {}
    for col in features:
        if col in ont:
            new_names[col] = f"{ont[col].name}:{col}"
    nodes = nodes.rename(columns=new_names)
    nodes = nodes.replace("", pd.NA)
    write_network(clean_name, nodes, link_table, _dir)

    st.log.debug(
        f"Network for {organism} has {len(nodes)} nodes and {len(link_table)}edges."
    )

    return nodes, link_table


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
    ) -> dict:
        """Generates a 3D layout for the graph.

        Args:
            G (nx.Graph): Graph to generate layout for.

        Returns:
            dict: Dictionary with node ids as keys and 3D positions as values.
        """
        layouter = Layouter()
        layouter.graph = G
        layouts = layouter.apply_layout(layout_algo, variables, feature_matrices)
        # for algo, layout in layouts.items():
        #     layout = np.array(list(layout.values()))
        #     pos = Layouter.normalize_pos(layout)
        #     layouts[algo] = pos
        return layouts

    def read_network(organism: str, _dir: str) -> tuple[nx.Graph, dict]:
        """Reads the graphml of the network and a json file with the link layouts.

        Args:
            organism (str): Organism from which the network originates from.

        Returns:
            tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
        """
        t1 = time()
        path = os.path.join(_dir, organism)
        nodes = pd.read_pickle(f"{path}/nodes.pickle")
        nodes = nodes.replace("", pd.NA)
        all_links = pd.read_pickle(f"{path}/links.pickle")
        all_links = all_links.replace("", pd.NA)
        st.log.debug(
            f"Loading data from pickles took {time() - t1} seconds.", flush=True
        )

        return nodes, all_links

    def write_node_layout(
        organism: str,
        G: nx.Graph,
        layouts: dict,
        _dir: str,
        overwrite: bool = False,
        layout_name: str = None,
        ranking: list[tuple[str, int]] = None,
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
        nodes = pd.DataFrame.from_dict(dict(G.nodes(data=True)), orient="index")
        nodes["r"] = 255
        nodes["g"] = 255
        nodes["b"] = 255
        nodes["a"] = 255 // 4

        has_gene_name = nodes["gene_name"].notna()
        nodes["ensembl"] = nodes[NT.name].copy()
        nodes.loc[has_gene_name, NT.name] = nodes.loc[has_gene_name, "gene_name"]
        # TODO add GO Terms to node Annotation
        nodes["attr"] = nodes.apply(
            lambda x: f"{x.get(NT.name)};{x.get(NT.uniprot)};{x.get(NT.description)};{x.get('ensembl')}",
            axis=1,
        )
        for idx, entry in enumerate(layouts.items()):
            name, layout = entry
            nodes["x"] = layout.loc[:, 0]
            nodes["y"] = layout.loc[:, 1]
            nodes["z"] = layout.loc[:, 2]
            if layout_name and len(layout_name) >= idx:
                name = layout_name[idx]
            st.log.debug(f"Writing node layout for {name} for {organism}.")
            tmp_nodes = nodes.copy()
            if "functional" in name and ranking:
                to_apply = tmp_nodes.index
                tmp = ranking.copy()
                colors = []
                while len(to_apply) > 0 and len(tmp) > 0:
                    column, _ = tmp.pop(0)
                    consider = tmp_nodes.loc[to_apply].copy()
                    consider = consider[consider[column].notna()]
                    if len(consider) == 0:
                        continue
                    while True:
                        color = np.random.choice(range(256), size=3)
                        hex = "#{:02x}{:02x}{:02x}".format(*color)
                        if hex not in colors:
                            colors.append(hex)
                            break
                    nodes.loc[consider.index, ["r", "g", "b"]] = color
                    tmp_nodes = tmp_nodes.drop(consider.index)
                    to_apply = [x for x in to_apply if x not in consider.index]

            file_name = os.path.join(_directory, f"{name}.csv")
            if os.path.isfile(file_name) and not overwrite:
                st.log.info(
                    f"Node layout for {name} for {organism} already exists. Skipping."
                )
                continue
            nodes[["x", "y", "z", "r", "g", "b", "a", "attr"]].to_csv(
                file_name, sep=",", header=False, index=False
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

    nodes, all_links = read_network(organism, _dir)
    all_links = all_links[:max_links]

    G = nx.from_pandas_edgelist(
        all_links[all_links[Evidences.any.value] > threshold],
        LiT.start,
        LiT.end,
        edge_attr=True,
    )
    layout_graph = G.copy()

    # nx.set_node_attributes(G, nodes.to_dict(orient="index"))
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
    feature_matrices = []
    matrix = nodes[[col for col in nodes.columns if ":GO" in col]]
    matrix = matrix.applymap(lambda x: 1, na_action="ignore")
    matrix = matrix.fillna(0)
    ranking = {
        col: int(matrix[col].sum()) for col in matrix.columns if matrix[col].sum() >= 10
    }
    ranking = sorted(ranking.items(), key=lambda x: x[1], reverse=True)
    for idx, layout in enumerate(tmp):
        file_name = os.path.join(_dir, organism, "nodes", f"{layout_name[idx]}.csv")
        if os.path.isfile(file_name) and not overwrite:
            st.log.info(
                f"Node layout for layout {layout} for {organism} already exists. Skipping."
            )
            layout_algo.remove(layout)
        else:
            st.log.info(
                f"{file_name} does not exist or overwrite is allowed. Generating layout."
            )
        if "functional" in layout:
            if max_num_features:
                filtered = ranking[:max_num_features]
            else:
                filtered = [x for x in ranking if x[1] > 50]
            matrix = matrix[[col for col, _ in filtered]]
            feature_matrices.append(matrix)
        else:
            feature_matrices.append(None)
    if debug:
        st.log.debug("DEBUG IS ON RANDOM LAYOUT")
        import random

        def pos():
            return [np.random.random() for _ in range(len(G.nodes))]

        layouts = {
            lay: pd.DataFrame({0: pos(), 1: pos(), 2: pos()}) for lay in layout_algo
        }
    else:
        layouts = gen_layout(layout_graph, layout_algo, variables, feature_matrices)
    st.log.info(f"Generated layouts. Used algorithms: {layout_algo}.")
    write_link_layouts(organism, all_links, _dir, overwrite_links)
    write_node_layout(
        organism,
        G,
        layouts,
        _dir,
        overwrite=overwrite,
        layout_name=layout_name,
        ranking=ranking,
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
    annot_file = os.path.join(directory, f"{tax_id}.gaf.gz")
    ont_file = os.path.join(directory, "..", "go-basic.obo")

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
        header=0,
        sep="\t",
        index_col=0,
    )
    # Filter out every entry which does not contains these three sources
    alias_table = alias_table.loc[
        alias_table["source"].isin(
            ["Ensembl_UniProt_AC", "BLAST_UniProt_AC", "BLAST_UniProt_GN_Name"]
        )
    ]
    description_table = pd.read_table(description_file, header=0, sep="\t", index_col=0)
    annot = pd.read_table(annot_file, comment="!", header=None, sep="\t")
    annot = annot.drop(columns=[0, 7, 11, 12, 13, 14, 15, 16])
    annot.columns = [
        "id",
        "symbol",
        "qualifier",
        "go",
        "db_reference",
        "evidence",
        "aspect",
        "name",
        "synonym",
    ]
    annot.index = annot["id"]
    ont = obo_parser.GODag(ont_file)
    return link_table, alias_table, description_table, annot, ont
