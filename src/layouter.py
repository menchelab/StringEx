import json
import os
from multiprocessing import Pool

import networkx as nx
import numpy as np
import pandas as pd
import swifter

from . import util
from .classes import Evidences
from .classes import LayoutAlgroithms as LA
from .classes import LayoutTags as LT
from .classes import LinkTags as LiT
from .classes import NodeTags as NT
from .classes import StringTags as ST
from .classes import VRNetzElements as VRNE
from .settings import log


class Layouter:
    """Simple class to apply a 3D layout algorithm to a networkx graph."""

    graph: nx.Graph = nx.Graph()

    @staticmethod
    def gen_graph(nodes: dict = None, links: dict = None) -> nx.Graph:
        """Generates a networkx graph based on a dict of nodes and links.

        Args:
            nodes (dict): contains all nodes that should be part of the graph with node ids as keys and nodes as values.
            links (dict): contains all links that should be part of the graph with link ids as keys and links as values.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        G = nx.Graph()
        G.add_nodes_from([(idx, node.dropna()) for idx, node in nodes.iterrows()])
        G.add_edges_from(
            [(start, end) for start, end in links[[LiT.start, LiT.end]].values.tolist()]
        )
        # for node_data in nodes:
        #     self.graph.add_node(node_data[NT.id], data=node_data)
        #     # self.node_map[node_data["id"]] = node_data
        # for link in links:
        #     self.graph.add_edge(link[LiT.start], link[LiT.end], data=link)
        #     # self.edge_map[(str(edge["s"]), str(edge["e"]))] = edge
        # self.network = {VRNE.nodes: nodes, VRNE.links: links}
        return G

    def read_from_vrnetz(self, file: str) -> nx.Graph:
        """Reads a graph from a VRNetz file.

        Args:
            file (str): Path to a VRNetz file.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        network = json.load(open(file))
        self.network = network
        nodes = network[VRNE.nodes]
        links = network[VRNE.links]
        return self.gen_graph(nodes, links)

    def get_node_data(self, node: str) -> dict:
        """Get the data of the desired node.

        Args:
            node (str): id of the desired node.

        Returns:
            dict: containing all data of a node
        """
        if "data" not in self.graph.nodes[node]:
            self.graph.nodes[node]["data"] = {}
        # self.graph.nodes[node].get("data",{}) # might work not sure
        return self.graph.nodes[node]["data"]

    def set_node_data(self, node: str, data: dict) -> None:
        """Set the dat of a desired node.

        Args:
            node (str):  id of the desired node.
            data (dict): containing all data of a node
        """
        self.graph.nodes[node]["data"] = data

    def read_from_grahpml(self, file: str) -> nx.Graph:
        """Read a graph from a graphml file.

        Args:
            file (str): path to the graphml file.

        Returns:
            networkx.Graph: Graph for which the layouts will be generated.
        """
        self.graph = nx.read_graphml(file)
        return self.graph

    def create_spring_layout(self, algo_variables: dict) -> dict:
        """Generates a spring layout for the Graph.

        Args:
            algo_variables (dict): contains variables for the algorithm.

        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        k = algo_variables.get("opt_dist")
        if k is not None:
            if k <= 0:
                k = None
        iterations = algo_variables.get("iterations", 50)
        threshold = algo_variables.get("threshold", 0.0001)
        return nx.spring_layout(
            self.graph, dim=3, k=k, iterations=iterations, threshold=threshold
        )

    def create_kamada_kawai_layout(self, algo_variables: dict) -> dict:
        """Generates a kamada kawai layout for the Graph.
        Args:
            algo_variables (dict): contains variables for the algorithm. Does not do anything.
        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        return nx.kamada_kawai_layout(self.graph, dim=3)

    def create_cartoGRAPH_layout(
        self,
        layout_algo: str,
        cg_variables: dict = None,
        feature_matrix: pd.DataFrame = None,
        max_num_features: int = None,
    ) -> dict:
        """Will pick the correct cartoGRAPHs layout algorithm and apply it to the graph. If cartoGRAPH is not installed an ImportError is raised.

        Args:
            layout_algo (str): layout algorithm to choose. possible algorithms are listed in setting.LayoutAlgroithms.
            cg_variables (dict, optional): contains algorithm variables. Defaults to None.

        Returns:
            dict: node ids as keys and three dimensional positions as values.
        """
        # try:
        import cartoGRAPHs as cg

        dim = 3

        if "tsne" in layout_algo:
            prplxty = cg_variables.get("prplxty", 50)
            density = cg_variables.get("density", 12)
            l_rate = cg_variables.get("l_rate", 200)
            steps = cg_variables.get("steps", 250)
            if "local" in layout_algo:
                try:
                    return cg.layout_local_tsne(
                        self.graph, dim, prplxty, density, l_rate, steps
                    )
                except Exception as e:
                    log.error(e)
                    return e
            elif "global" in layout_algo:
                return cg.layout_global_tsne(
                    self.graph, dim, prplxty, density, l_rate, steps
                )
            elif "importance" in layout_algo:
                return cg.layout_importance_tsne(
                    self.graph, dim, prplxty, density, l_rate, steps
                )
            elif "functional" in layout_algo:
                if feature_matrix is None:
                    feature_matrix = self.get_feature_matrix(
                        self.graph, max_num_features
                    )
                if feature_matrix is None:
                    return ValueError("Unable to construct feature matrix!")
                return cg.layout_functional_tsne(
                    self.graph, feature_matrix, dim, prplxty, density, l_rate, steps
                )
        if "umap" in layout_algo:
            n_neighbors = cg_variables.get("n_neighbors", 10)
            spread = cg_variables.get("spread", 1.0)
            min_dist = cg_variables.get("min_dist", 0.1)
            if "local" in layout_algo:
                return cg.layout_local_umap(
                    self.graph, dim, n_neighbors, spread, min_dist
                )
            elif "global" in layout_algo:
                return cg.layout_global_umap(
                    self.graph, dim, n_neighbors, spread, min_dist
                )
            elif "importance" in layout_algo:
                return cg.layout_importance_umap(
                    self.graph, dim, n_neighbors, spread, min_dist
                )
            elif "functional" in layout_algo:
                if feature_matrix is None:
                    feature_matrix = self.get_feature_matrix(
                        self.graph, max_num_features
                    )
                if feature_matrix is None:
                    return ValueError("Unable to construct feature matrix!")
                return cg.layout_functional_umap(
                    self.graph, feature_matrix, dim, n_neighbors, spread, min_dist
                )
        elif "topographic" in layout_algo:
            # d_z = a dictionary with keys=G.nodes and values=any int/float assigned to a node
            posG2D = nx.Graph()
            z_list = [np.random.random() for i in range(0, len(list(posG2D.nodes())))]
            d_z = dict(zip(list(posG2D.nodes()), z_list))
            return cg.layout_topographic(posG2D, d_z)

        elif "geodesic" in layout_algo:
            d_radius = 1
            n_neighbors = 8
            spread = 1.0
            min_dist = 0.0
            DM = None
            # radius_list_norm = preprocessing.minmax_scale((list(d_radius.values())), feature_range=(0, 1.0), axis=0, copy=True)
            # d_radius_norm = dict(zip(list(G.nodes()), radius_list_norm))
            return cg.layout_geodesic(
                self.graph, d_radius, n_neighbors, spread, min_dist, DM
            )

    def apply_layout(
        self,
        layout_algo: str = None,
        algo_variables: dict = {},
        feature_matrices: list[pd.DataFrame] = None,
        max_num_features: int = None,
    ) -> dict[str, list[float]]:
        """Applies a layout algorithm and adds the node positions to nodes in the self.network[VRNE.nodes] list.

        Args:
            layout_algo (str, optional): layout algorithm to choose. possible algorithms are listed in setting.LayoutAlgroithms.. Defaults to None.
            algo_variables (dict, optional): Contains algorithm variables. Defaults to None.. Defaults to {}.

        Returns:
            dict[str,list[float]]: with node ids as keys and three dimensional xnode positions as values.
        """
        layouts = {}
        if isinstance(layout_algo, str):
            layout_algo = [layout_algo]
        for idx, algo in enumerate(layout_algo):
            if algo is None:
                """Select default layout algorithm"""
                algo = LA.spring
            if LA.cartoGRAPH in algo:
                log.debug(f"Applying layout: {algo}.", flush=True)
                layout = self.create_cartoGRAPH_layout(
                    algo, algo_variables, feature_matrices[idx], max_num_features
                )
                if isinstance(layout, ValueError):
                    log.error(
                        "Error in executing cartoGRAPHs layout. Create a layout with spring instead."
                    )
                    layout = self.create_spring_layout(algo_variables)
            else:
                lay_func = {
                    LA.spring: self.create_spring_layout,
                    LA.kamada_kawai: self.create_kamada_kawai_layout,
                }
                log.debug(f"Applying layout: {algo}", flush=True)
                layout = lay_func[algo](
                    algo_variables
                )  # Will use the desired layout algorithm

            lay = np.array(list(layout.values()))
            x = lay[:, 0]
            y = lay[:, 1]
            z = lay[:, 2]

            def normalize_pos(x):
                x += abs(min(x))
                x /= max(x)
                return x

            pos = pd.DataFrame([x, y, z]).T
            pos = pos.apply(normalize_pos, axis=0)
            layouts[algo] = pos
        return layouts

    @staticmethod
    def normalize_pos(layout: dict):

        x = layout[:, 0]
        y = layout[:, 1]
        z = layout[:, 2]

        def norm(x):
            x += abs(min(x))
            x /= max(x)
            return x

        pos = pd.DataFrame([x, y, z]).T
        pos = pos.swifter.progress_bar(False).apply(norm)
        return pos

    @staticmethod
    def add_layout_to_vrnetz(
        nodes: pd.DataFrame, layout: dict, layout_name: str
    ) -> None:
        """Adds the points of the generated layout to the underlying VRNetz

        Args:
            layout (dict): Dictionary containing node ids as keys and a 3-tuple of coordinates as values.
            layout_name (str): Name of the layout to be added to the VRNetz.
        """
        if NT.layouts in nodes:

            def extract_cy(x):
                if NT.layouts not in x:
                    return x
                layout = x[NT.layouts][0]
                x["cy_pos"] = layout["p"]
                x["cy_col"] = layout["c"]
                x["size"] = layout["s"]
                return x

            nodes = nodes.swifter.progress_bar(False).apply(extract_cy, axis=1)

        nodes[layout_name + "2d_pos"] = layout.swifter.progress_bar(False).apply(
            lambda x: [x[0], x[1], 0], axis=1
        )
        nodes[layout_name + "_pos"] = layout.swifter.progress_bar(False).apply(
            lambda x: list(x), axis=1
        )

        if "cy_pos" and "cy_col" in nodes:
            # nodes[layout_name+"_col"] = nodes["cy_col"]
            coords = np.array([np.array(x) for x in nodes["cy_pos"]])
            pos = Layouter.normalize_pos(coords)

            nodes["cy_pos"] = pos.swifter.progress_bar(False).apply(
                lambda x: [x[0], x[1], 0], axis=1
            )

            def extract_color(x):
                """Scale alpha channel (glowing effect) with node size (max size = 1"""
                col = x["cy_col"] + [int(255 * x["size"])]
                return col

            max_size = max(nodes["size"])
            nodes["size"] = (
                nodes["size"].swifter.progress_bar(False).apply(lambda x: x / max_size)
            )
            nodes["cy_col"] = (
                nodes[["cy_col", "size"]]
                .swifter.progress_bar(False)
                .apply(extract_color, axis=1)
            )

        return nodes

    @staticmethod
    def gen_evidence_layouts(
        links: pd.DataFrame,
        evidences: dict = None,
        stringify: bool = False,
    ) -> list[dict[str, object]]:
        """Set the link color for each STRING evidence type. Based on the score the link opacity is scaled.

        Args:
            network (dict): Network dictionary.
            evidences (dict[str, tuple[float, float, float, float]] or None, optional): Contains all possible evidence types and their corresponding color. Defaults to None.

        Returns:
            dict: Network dictionary with the link layout information.
        """
        # Set up the colors for each evidence type
        if evidences is None:
            evidences = Evidences.get_default_scheme()
        log.debug(f"Handling evidences...", flush=True)

        if ST.stringdb_score in links.columns:
            links = links.rename(columns={ST.stringdb_score: Evidences.any.value})

        elif Evidences.any.value not in links.columns:
            links[Evidences.any.value] = [1 for _ in range(len(links))]

        def extract_score(x):
            evidences = [
                ev for ev in Evidences.get_all_evidences_except_any() if ev in x.keys()
            ]
            if len(evidences) == 0:
                value = None
            else:
                value = max(x[evidences])
            x[Evidences.any.value] = value
            return x

        to_replace = links[Evidences.any.value].isnull()
        links[to_replace] = (
            links[to_replace].swifter.progress_bar(False).apply(extract_score, axis=1)
        )

        colors = [
            Layouter.handle_evidences(ev, color, links, stringify)
            for ev, color in evidences.items()
        ]
        for ev, data in zip(evidences.keys(), colors):
            if data is None:
                continue
            links[ev + "_col"] = data
        return links

    @staticmethod
    def handle_evidences(ev, color, links, stringify):
        def gen_color(x, color):
            x = color[:3] + (int(x * 255),)
            return x

        if ev not in links.columns:
            if stringify:
                links[ev] = [int(0) for _ in range(len(links))]
            else:
                return
        with_score = links[links[ev] > 0.0][ev]
        this = with_score.swifter.progress_bar(False).apply(gen_color, args=(color,))
        return this

    @staticmethod
    def get_feature_matrix(
        G: nx.Graph or pd.DataFrame,
        max_num_features: int = None,
    ) -> pd.DataFrame:
        if max_num_features is None:
            max_num_features = 100
        if isinstance(G, nx.Graph):
            nodes = pd.DataFrame.from_dict(dict(G.nodes(data=True)), orient="index")
        elif isinstance(G, pd.DataFrame):
            nodes = G
        all_columns = list(nodes.columns)
        new_cols = {}
        n = nodes.size
        feature_matrix = pd.DataFrame(index=range(n))
        while len(all_columns) > 0:
            column = all_columns.pop()
            data = nodes[column]
            if (
                pd.api.types.is_string_dtype(data)
                and not pd.api.types.is_bool_dtype(data)
                and not pd.api.types.is_numeric_dtype(data)
                and not pd.api.types.is_list_like(data)
            ):
                strings = data.unique()
                if strings.size <= nodes.size * 0.05:
                    nodes = nodes.drop(columns=[column])
                    continue
                log.debug(f"Handling column {column}...")
                for string in strings:
                    if string in feature_matrix.columns:
                        continue
                    series = (
                        nodes[column].apply(lambda x: 1 if x == string else 0).copy()
                    )
                    series.name = string
                    feature_matrix = pd.concat([feature_matrix, series], axis=1)

            elif (
                pd.api.types.is_numeric_dtype(data)
                and not pd.api.types.is_bool_dtype(data)
                and not pd.api.types.is_list_like(data)
            ):
                numbers = nodes[column].unique()
                if numbers.size <= nodes.size * 0.05:
                    nodes = nodes.drop(data)
                    continue
                log.debug(f"Handling column {column}...")
                new_cols = {}
                for number in numbers:
                    if number in feature_matrix.columns:
                        continue
                    series = (
                        nodes[column].apply(lambda x: 1 if x == number else 0).copy()
                    )
                    series.name = number
                    feature_matrix = pd.concat([feature_matrix, series], axis=1)
            elif pd.api.types.is_list_like(data):
                log.debug(f"Handling column {column}...")
                new_values = set()
                for _, row in nodes.iterrows():
                    if not pd.api.types.is_list_like(row[column]):
                        continue
                    for val in row[column]:
                        new_values.add(val)
                tmp = pd.DataFrame(data)
                for val in new_values:
                    if val in tmp.columns:
                        continue
                    series = pd.Series([0 for _ in range(n)], index=nodes.index)
                    series.name = val
                    tmp = pd.concat([feature_matrix, series], axis=1)

                def gen_feature(x, column):
                    if not pd.api.types.is_list_like(x[column]):
                        return None
                    for val in x[column]:
                        x[val] = 1
                    return x[[val for val in x[column]]]

                tmp = nodes.swifter.apply(gen_feature, args=(column,), axis=1)
                nodes = nodes.drop(columns=[column])
                feature_matrix = pd.concat([feature_matrix, tmp], axis=1)

        for col in feature_matrix.columns:
            new_cols[col] = feature_matrix[col].notna().sum()
        new_cols = sorted(new_cols.items(), key=lambda x: x[1], reverse=True)
        new_cols = new_cols[:max_num_features]
        columns = [col[0] for col in new_cols]
        feature_matrix = feature_matrix.reindex(columns=columns, fill_value=0)
        if len(feature_matrix.columns) == 0:
            return None
        log.debug(
            f"The feature matrix consists of {len(feature_matrix.columns)} new features.",
            flush=True,
        )
        return feature_matrix


if __name__ == "__main__":
    import os

    layouter = Layouter()
    layouter.read_from_vrnetz(
        os.path.abspath(
            f"{__file__}/../../static/networks/STRING_network_-_Alzheimer's_disease.VRNetz"
        )
    )
    layouter.apply_layout()
