# Deprecated
from extract_colors_from_style import get_node_mapping


def apply_style_workflow(graph: nx.Graph, style: str) -> nx.Graph:
    color_mapping = get_node_mapping(style)
    if color_mapping is None:
        return graph
    mapping_type = color_mapping["type"]
    log.info(f"Color mapping extracted from: {style}.xml. Mapping Type: {mapping_type}")
    graph = colorize_nodes(graph, color_mapping)
    log.info(f"Colored nodes according to color mapping.")
    return graph


def protein_query_workflow(
    parser: CytoscapeParser, p_query: list[str], **kwargs
) -> None:
    """Fetches a network for given protein query."""
    query = StringProteinQuery(query=p_query, **kwargs)
    log.info(f"Command as list:{query.cmd_list}")
    parser.exec_cmd(query.cmd_list)


def disease_query_workflow(parser: CytoscapeParser, disease: str, **kwargs) -> None:
    """Fetches a network for given disease query."""
    query = StringDiseaseQuery(disease=disease, **kwargs)
    log.info(f"Command as list:{query.cmd_list}")
    parser.exec_cmd(query.cmd_list)


def compound_query_workflow(
    parser: CytoscapeParser, query: list[str], **kwargs
) -> None:
    """Fetches a network for given compound query."""
    query = StringCompoundQuery(query=query, **kwargs)
    log.info(f"Command as list:{query.cmd_list}")
    parser.exec_cmd(query.cmd_list)


def pubmed_query_workflow(parser: CytoscapeParser, pubmed: list[str], **kwargs) -> None:
    """Fetches a network for given pubmed query."""
    query = StringPubMedQuery(pubmed=pubmed, **kwargs)
    log.info(f"Command as list:{query.cmd_list}")
    parser.exec_cmd(query.cmd_list)
    print(query.cmd_list)


def export_network_workflow(
    parser: CytoscapeParser,
    filename: str = None,
    network: str = None,
    keep_output: bool = True,
    layout_algo: str = None,
    **kwargs,
) -> tuple[Layouter, str]:
    """Exports a network as GraphML file, generates a 3D layout."""
    networks = parser.get_network_list()
    if network is None:
        network = list(networks.keys())[0]
    if filename is None:
        filename = network
    filename = filename.replace(" ", "_")
    network_loc = f"{_NETWORKS_PATH}/{filename}"
    network_file = f"{network_loc}.VRNetz"

    parser.export_network(filename=network_loc)
    log.info(f"Network exported: {network}")

    # generate a 3D layout
    layouter = apply_layout_workflow(f"{network_loc}.VRNetz", layout_algo)

    # if keep_output is False, we remove the tmp GraphML file
    if not keep_output:
        os.remove(network_file)
        log.info(f"Removed tmp file: {network_file}")

    return layouter, filename


# TODO: Networkx export with separate table export. Does not work do fails in matching node/edge names to SUIDs
def parse_network(parser: CytoscapeParser, network_index=None, **kwargs):
    if network_index is None:
        network_index = 0
    networks = parser.get_network_list()
    network = list(networks.keys())[network_index]
    graph = parser.get_networkx_network(network)
    # node_columns, edge_columns = parser.export_table(network)
    nx.draw(graph)
    plt.show()


# TODO directly create a networkx network
