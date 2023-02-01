import gzip
import json
import os
import tarfile
import pickle
from time import time

import networkx as nx
import pandas
import numpy as np
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
):
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

    directory = os.path.join(networks_directory, clean_name)

    link_file = os.path.join(directory, f"{tax_id}.protein.links.detailed.v11.5.txt")

    filtered = os.path.join(
        directory, f"{tax_id}.protein.links.detailed.v11.5.filtered.txt"
    )

    # if os.path.isfile(filtered):
    #     link_file = filtered

    alias_file = os.path.join(directory, f"{tax_id}.protein.aliases.v11.5.txt")
    description_file = os.path.join(directory, f"{tax_id}.protein.info.v11.5.txt")

    rename_dict = {"protein1":LiT.start,
        "protein2":LiT.end,
        "neighborhood":Evidences.stringdb_neighborhood.value,
        "fusion":Evidences.stringdb_fusion.value,
        "cooccurence":Evidences.stringdb_cooccurrence.value,
        "coexpression":Evidences.stringdb_coexpression.value,
        "experimental":Evidences.stringdb_experiments.value,
        "database":Evidences.stringdb_databases.value,
        "textmining":Evidences.stringdb_textmining.value,
        "combined_score":Evidences.any.value,
        "homology":Evidences.stringdb_similarity.value,}
    type_dict = {
        LiT.start:str,
        LiT.end:str,
        Evidences.stringdb_neighborhood.value:np.int64,
        Evidences.stringdb_fusion.value:np.int64,
        Evidences.stringdb_cooccurrence.value:np.int64,
        Evidences.stringdb_coexpression.value:np.int64,
        Evidences.stringdb_experiments.value:np.int64,
        Evidences.stringdb_databases.value:np.int64,
        Evidences.stringdb_textmining.value:np.int64,
        Evidences.any.value:np.int64,
        Evidences.stringdb_similarity.value:np.int64,
    }

    network_table = pandas.read_table(link_file, header=0, sep=" ")
    for default_col, new_col in rename_dict.items():
        if default_col in network_table.columns:
            network_table = network_table.rename(columns={default_col:new_col})
        elif new_col not in network_table.columns:
            network_table[new_col] = [0 for _ in range(len(network_table))]
    network_table = network_table.astype(type_dict)

    n = len(network_table)
    if n > MAX_NUM_LINKS:
        st.log.info(f"Too many links. Will filter them.")
        network_table = network_table.sort_values(
            [Evidences.stringdb_experiments.value, Evidences.any.value], ascending=False
        )
        network_table = network_table.reset_index(drop=True)
        network_table = network_table.truncate(after=MAX_NUM_LINKS - 1)
        network_table.to_csv(filtered, sep=" ", index=False)
    st.log.info("Filtered and sorted...")
    alias_table = pandas.read_table(
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

    description_table = pandas.read_table(
        description_file, header=0, sep="\t", index_col=0
    )
    st.log.info("Generating graph...")
    return gen_graph(
        network_table,
        alias_table,
        description_table,
        organism,
        clean_name,
        networks_directory,
        last_link,
    )


def gen_graph(
    network_table: pandas.DataFrame,
    alias_table: pandas.DataFrame,
    description_table: pandas.DataFrame,
    organism: str,
    clean_name: str,
    _dir: str,
    last_link: int or None = None,
    threshold: int = 0,
) -> tuple[nx.Graph, dict]:
    """Extracts data from the STRING database files and constructs a graph representing the protein-protein interaction network.

    Args:
        network_table (pandas.DataFrame): Data Frame containing all links of the network.
        alias_table (pandas.DataFrametr): Data Frame containing all aliases of the proteins.
        description_table (pandas.DataFrame): Data Frame containing Descriptions of the proteins.
        organism (str): Organism from which the network originates from.
        last_link (int or None, optional): FOR DEBUGGING: Integer of the last link to be processed. Defaults to None.
        threshold (int): Score threshold, every edge having an experimental score larger than this value is used for layout calculation. Defaults to 0.

    Returns:
        tuple[nx.Graph, dict]: Graph representing the protein-protein interaction network and a dictionary containing the nodes of the graph.
    """

    def extract_nodes(
        # idx: int,
        # identifier: str,
        node:dict,
        alias_table: pandas.DataFrame,
        description_table: pandas.DataFrame,
    ) -> tuple[dict, int, pandas.DataFrame, pandas.DataFrame]:
        def extract_unirot_id(alias: pandas.DataFrame) -> list:
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

        def extract_gene_name(alias: pandas.DataFrame):
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

        # node = {}
        # node[NT.id] = int(idx)
        # idx += 1
        # node[NT.name] = identifier.split(".")[1]

        # get uniprot id(s)
        identifier = node[NT.name]
        node[NT.name] = node[NT.name].split(".")[1]
        alias = alias_table.loc[alias_table.index == identifier]
        if not alias.empty:
            alias.drop(identifier, axis=0)
            uniprot = extract_unirot_id(alias)
        else:
            uniprot = None
        node["uniprot"] = uniprot

        gene_name = extract_gene_name(alias)
        if gene_name:
            node["gene_name"] = gene_name

        # node[NT.species] = species
        annotation = description_table.at[identifier, "annotation"]

        if annotation != "annotation not available":
            node[NT.description] = annotation

        return node

    species = Organisms.get_scientific_name(organism)
    taxid = Organisms.get_tax_ids(organism)

    if last_link is None:
        last_link = len(network_table)
    else:
        if last_link > len(network_table):
            last_link = len(network_table)

    network_table = network_table[
        network_table[LiT.start].notna() & network_table[LiT.end].notna()
    ]
    st.log.info("Dropped links where start or end is NA.")
    network_table[[ev.value for ev in Evidences]] = network_table[[ev.value for ev in Evidences]].div(1000)
    st.log.info("Divided by 1000!")

    st.log.info("Extracting nodes...")
    nodes = pandas.DataFrame(columns=[NT.name, NT.species, NT.description])
    concat = pandas.concat([network_table[LiT.start], network_table[LiT.end]])
    nodes[NT.name] = concat.unique()
    nodes[NT.species] = species
    nodes = nodes.apply(extract_nodes, axis=1,args=(alias_table, description_table))
    st.log.info("Nodes extracted!")
    def get_index(elem):
        elem[LiT.start] = nodes[nodes[NT.name] == elem[LiT.start].split(".")[1]].index[0]
        elem[LiT.end] = nodes[nodes[NT.name] == elem[LiT.end].split(".")[1]].index[0]
        return elem
    
    st.log.info("Mapping nodes to indices...")
    network_table = network_table.apply(get_index, axis=1)
    st.log.info("Mapped nodes to indices!")
    no_uniprot = nodes[nodes["uniprot"].isna() & nodes["gene_name"].notna()]
    nodes = map_gene_names_to_uniprot(nodes, no_uniprot, taxid)
    write_network(clean_name, nodes, network_table, _dir)

    st.log.info(
        f"Network for {organism} has {len(nodes)} nodes and {len(network_table)}edges."
    )

    return nodes, network_table


def map_gene_names_to_uniprot(nodes: pandas.DataFrame, missing_annot: dict, taxid: str) -> nx.Graph:
    """Maps gene names to uniprot ids and adds them to the nodes.

    Args:
        G (nx.Graph): Graph Containing all nodes of the network.
        map_gene_name (dict): dict that maps node ids to gene names.
        taxid (str): taxonomic id of the organism.

    Returns:
        nx.Graph: Same graph as the input graph, but with updated uniprot ids.
    """
    if not missing_annot.empty:
        st.log.debug("Mapping gene names to uniprot ids...")
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
            nodes.iat[idx,"uniprot"] = primaryAccession

    return nodes


def write_network(
    organism: str, nodes: pandas.DataFrame, processed_network: pandas.DataFrame, _dir: str
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
    st.log.debug(f"Writing pickle data took {time() - t1} seconds.")


def construct_layouts(
    organism: str,
    _dir: str,
    layout_algo: list[str] = None,
    variables: dict = None,
    overwrite: bool = False,
    overwrite_links: bool = False,
    threshold: float = 0.4,
    max_links: int = st.MAX_NUM_LINKS
) -> None:
    """Constructs the layouts for the network and compress them into a tar file.

    Args:
        organism (str): Organism which should be processed.
        _dir (str): Path to the directory in which all files are saved in.
        layout_algo (str): Defines the layout algorithm which should be used.
        variables (dict): Defines the variables of the respective layout algorithm.
    """

    def gen_layout(
        G: nx.Graph, layout_algo: str = None, variables: dict = None
    ) -> dict:
        """Generates a 3D layout for the graph.

        Args:
            G (nx.Graph): Graph to generate layout for.

        Returns:
            dict: Dictionary with node ids as keys and 3D positions as values.
        """
        layouter = Layouter()
        layouter.graph = G
        layouts = layouter.apply_layout(layout_algo, variables)
        for algo,layout in layouts.items():
            layout = np.array(list(layout.values()))
            pos = Layouter.normalize_pos(layout)
            layouts[algo] = pos
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
        nodes = pandas.read_pickle(f"{path}/nodes.pickle")
        all_links = pandas.read_pickle(f"{path}/links.pickle")
        st.log.debug(f"Loading data from pickles took {time() - t1}) seconds.")

        return nodes, all_links

    def write_node_layout(
        organism: str, G: nx.Graph, layouts: dict, _dir: str, overwrite: bool = False
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
        nodes = pandas.DataFrame.from_dict(dict(G.nodes(data=True)), orient='index')
        nodes["r"] = 255
        nodes["g"] = 255
        nodes["b"] = 255
        nodes["a"] = 255//2
        nodes["attr"] = nodes.apply(lambda x: f"{x.get(NT.name)};{x.get(NT.uniprot)};{x.get(NT.description)}", axis=1)
        for name, layout in layouts.items():
            nodes["x"] = layout.loc[:,0]
            nodes["y"] = layout.loc[:,1]
            nodes["z"] = layout.loc[:,2]
            file_name = os.path.join(_directory, f"{name}_nodes.csv")
            if os.path.isfile(file_name) and not overwrite:
                st.log.info(
                    f"Node layout for {name} for {organism} already exists. Skipping."
                )
                continue
            nodes[['x','y','z','r','g','b','a','attr']].to_csv(file_name, sep=',', header=False, index=False)   
            print(nodes[['x','y','z','r','g','b','a','attr']])
            st.log.info(f"Node layout for {organism} has been written to {file_name}.")

    def write_link_layouts(
        organism: str, all_links: pandas.DataFrame, _dir: str, overwrite: bool = False,threshold:float=0.4,
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
        _directory = os.path.join(_dir, organism)
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
            all_links[ev] = all_links[ev].apply(get_link_colors,args=(color_scheme[ev],))

            ev_text = all_links[all_links[ev].apply(lambda x: x[3] > 0)]
            ev_text = ev_text[[ev, LiT.start, LiT.end]]
            if not ev_text.empty:
                ev_text["r"] = ev_text[ev].apply(lambda x: x[0])
                ev_text["g"] = ev_text[ev].apply(lambda x: x[1])
                ev_text["b"] = ev_text[ev].apply(lambda x: x[2])
                ev_text["a"] = ev_text[ev].apply(lambda x: x[3])
            ev_text = ev_text.drop(columns=ev)
            ev_text.to_csv(file_name, index=False,header=False)
            st.log.info(
                f"link layout for evidence {ev} for {organism} has been written to {file_name}."
            )

    nodes, all_links = read_network(organism, _dir)
    all_links = all_links[:max_links]
    G = nx.from_pandas_edgelist(all_links[all_links[Evidences.any.value]>threshold], LiT.start, LiT.end, edge_attr=True)

    nodes = nodes.fillna(value="")
    nx.set_node_attributes(G,nodes.to_dict(orient="index"))
    not_ind = [idx for idx in nodes.index if idx not in G.nodes]
    missing_nodes = nodes.loc[not_ind]
    if len(missing_nodes) > 0:
       G.add_nodes_from((idx,{k:v for k,v in row.items()}) for idx,row in missing_nodes.iterrows())
    # Map gene names to uniprot ids and add them to the nodes.
    tmp = layout_algo.copy()
    for layout in tmp:
        file_name = os.path.join(_dir, organism, f"{layout}_nodes.csv")
        if os.path.isfile(file_name) and not overwrite:
            st.log.info(
                f"Node layout for layout {layout} for {organism} already exists. Skipping."
            )
            layout_algo.remove(layout)
        else:
            st.log.info(
                f"{file_name} does not exist or overwrite is allowed. Generating layout."
            )
    layouts = gen_layout(G, layout_algo, variables)
    st.log.info(f"Generated layouts. Used algorithms: {layout_algo}.")
    write_link_layouts(organism, all_links, _dir, overwrite_links,threshold)
    write_node_layout(organism, G, layouts, _dir, overwrite=overwrite)
