import os

try:
    import GlobalData as GD
except ModuleNotFoundError:
    pass
import networkx as nx
from bs4 import BeautifulSoup as bs
from PIL import ImageColor

from . import settings as st
from .settings import LayoutTags as LT
from .settings import NodeTags as NT
from .settings import logger


def prepare_networkx_network(G: nx.Graph, positions: dict = None) -> tuple[dict, dict]:
    """Transforms a basic networkx graph into a correct data structure to be uploaded by the Cytoscape uploader. If the positions are not given, the positions are calculated using the spring layout algorithm of networkx."""
    if positions is None:
        positions = nx.spring_layout(G, dim=3)
    nodes_data = {}
    edges_data = {}
    for node in G.nodes():
        nodes_data[node] = {
            "pos": positions[node],
            "uniprotid": node,
            "display name": "Gene Name of the Protein",
        }
    for edge in G.edges():
        edges_data[edge] = {"source": edge[0], "target": edge[1]}
    return nodes_data, edges_data


def colorize_nodes(
    G: nx.Graph,
    color_mapping: dict,
) -> nx.Graph:
    """Colorizes the nodes of a networkx graph using a color mapping. Works for discrete, continuous, and passthrough mappings."""
    if color_mapping["type"] == "discrete":
        """For each node a color is assigned, if not it get the default color value."""
        for node in G.nodes:
            name = G.nodes[node]["name"]
            if name in color_mapping:
                color = color_mapping[name]
            else:
                color = color_mapping["default"]
            G.nodes[node]["color"] = color
    elif color_mapping["type"] == "continuous":
        """Uses the Value which is stored respective column a defines the color respectively."""
        default_color = color_mapping["default"]
        column = color_mapping["column"]
        for node in G.nodes:
            color = default_color
            mapping_points = {
                k: v for k, v in color_mapping.items() if isinstance(k, float)
            }
            if column in G.nodes[node].keys():
                node_value = float(G.nodes[node][column])
                for point in mapping_points:
                    color = color_mapping["default"]
                    flag = False
                    if node_value < point:
                        color = mapping_points[point][0]
                        flag = True
                    elif node_value == point:
                        color = mapping_points[point][1]
                        flag = True
                    elif node_value > point:
                        color = mapping_points[point][2]
                    if flag:
                        break
            G.nodes[node]["color"] = color
    elif color_mapping["type"] == "passthrough":
        """Uses the Value which is stored respective column."""
        column = color_mapping["column"]
        for node in G.nodes:
            if column in G.nodes[node]:
                color = G.nodes[node][column]
                # Color values are most likely hex values. We convert them to RGBA values.
                color = ImageColor.getcolor(color, "RGB") + (255,)
                G.nodes[node]["color"] = color
    return G


def find_cy_layout(node):
    cy_layout, idx = None, None
    if NT.layouts in node:
        for idx, layout in enumerate(node[NT.layouts]):
            if layout[LT.name] == LT.cy_layout:
                cy_layout = layout
                break
    return cy_layout, idx


def clean_filename(name: str) -> str:
    """Cleans the project name to be used in the file names."""
    name = name.replace(" ", "_")
    name = name.replace("/", "_")
    name = name.replace("'", "")
    name = name.replace("´", "")
    name = name.replace("`", "")
    name = name.replace("'", "")
    name = name.replace("“", "")
    name = name.replace(",", "_")
    name = name.replace(".", "_")
    name = name.replace("-", "_")
    name = name.replace("–", "_")
    name = name.replace("#", "_")
    return name


def pepare_uploader():
    GD.sessionData["layoutAlgos"] = st.LayoutAlgroithms.all_algos
    GD.sessionData["actAlgo"] = st.LayoutAlgroithms.spring
    GD.sessionData["organisms"] = st.Organisms.all_organisms

    with open(
        os.path.join(st._FLASK_TEMPLATE_PATH, "string_upload_tab_template.html"), "r"
    ) as f:
        soup = bs(f, "html.parser")

    # Add layout options to the layout dropdown menu
    selector = soup.find("select", {"id": "string_algo"})
    for algo in GD.sessionData["layoutAlgos"]:
        selector.append(
            bs(f"""<option value="{algo}">{algo}</option>""", "html.parser")
        )

    with open(
        os.path.join(st._FLASK_TEMPLATE_PATH, "string_upload_tab.html"), "w"
    ) as f:
        f.write(str(soup.prettify()))

    # Add organism options to the organism dropdown menu
    with open(
        os.path.join(st._FLASK_TEMPLATE_PATH, "string_map_tab_template.html"), "r"
    ) as f:
        soup = bs(f, "html.parser")
    selector = soup.find("select", {"id": "string_organism"})

    for algo in GD.sessionData["organisms"]:
        selector.append(
            bs(f"""<option value="{algo}">{algo}</option>""", "html.parser")
        )
    with open(os.path.join(st._FLASK_TEMPLATE_PATH, "string_map_tab.html"), "w") as f:
        f.write(str(soup.prettify()))


if __name__ == "__main__":
    G = nx.Graph()
    G.add_edge("O15552", "Q76EI6")
    print(prepare_networkx_network(G))
