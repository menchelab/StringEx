import numpy as np
import src.settings as st
import pandas as pd
import time
from interactomes import data_io
from interactomes import check_feature_matrices
from interactomes import functional_annotations as fa
import seaborn as sns
from src.classes import Organisms
from src.classes import NodeTags as NT
from src.classes import StringTags as ST
import os
from src.layouter import visualize_layout
from interactomes import retrieve_functional_enrichment as rfe


def color_layout(
    n,
    algo,
    category,
    feature_matrix: pd.DataFrame,
    eps: float = None,
    normalize: bool = False,
    pos=None,
    preview_layout: bool = False,
):
    colors = pd.Series([[1, 1, 1, 1] for _ in range(n)])
    df = pd.DataFrame(index=range(n))
    df["cluster"] = None

    if "functional" in algo and category is not None:
        has_features = feature_matrix.any(axis=1)
        st.log.debug(f"There are {has_features.sum()} nodes with at least one feature")

        st.log.debug("Adding colors to functional clusters..")
        to_color = pd.Series(index=colors[has_features].index)
        feature_matrix = feature_matrix[has_features]
        feature_pos = pd.DataFrame(pos)[has_features]

        to_color, cluster = clustering(to_color, feature_matrix, feature_pos)
        cluster_information = pd.Series(cluster, index=to_color.index)
        df["cluster"] = cluster_information
        # to_color = feature_coloring(to_color, feature_matrix, category)
        colors.update(to_color)
    else:
        st.log.debug(f"SKIPPING {algo} {category}")
    colors = np.array(colors.tolist())
    # Invert colors and normalize between 0.1 and 1 to make them at least visible
    if not colors.max() == colors.min():
        colors = 0.5 - (colors - 0.5)
        colors = 0.9 * (colors - colors.min()) / (colors.max() - colors.min()) + 0.1
    else:
        print("All colors are the same")
        colors = np.ones_like(colors)
    for i in range(3):
        st.log.debug(f"{colors[:, i].min()}, {colors[:, i].max()}")
    if preview_layout:
        st.log.debug("VISUALIZING LAYOUT")
        visualize_layout(
            pos,
            colors[:, :3],
        )
    if normalize:
        return colors, cluster

    colors *= 255
    colors = colors.astype(int)
    df[["r", "g", "b", "a"]] = colors
    return df[["r", "g", "b", "a", "cluster"]]


def clustering(to_color, fm, pos, eps=None, min_samples=None):
    import umap
    from matplotlib import pyplot as plt
    from sklearn.decomposition import PCA
    import hdbscan

    # fm = fm[:5000]
    if "annotations" in fm.columns:
        fm = fm.drop(columns="annotations")
    feature_count = fm.sum(axis=0)
    min_cs = feature_count.min()
    max_cs = feature_count.max()
    min_cs = max(50, feature_count.min())
    if min_cs > 100:
        min_cs = 50
    if eps is None:
        eps = 0.007
    if min_samples is None:
        min_samples = 20
    st.log.debug("MIN_CS = " + str(min_cs))
    # model_varaibles(fm, pos, min_cs, eps)
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cs,
        max_cluster_size=max_cs,
        cluster_selection_method="leaf",
        cluster_selection_epsilon=eps,
        min_samples=min_samples,
    )
    clusterer.fit_predict(pos)
    labels = clusterer.labels_
    cluster_labels = [x for x in labels if x >= 0]
    labels = set(cluster_labels)
    st.log.debug(f"FOUND CLUSTERS: {len(labels)}")
    color_palette = sns.color_palette("bright", len(labels))
    not_clustered = [0, 0, 0, 0.75]
    cluster_colors = [
        color_palette[x] + (0.5,) if x >= 0 else not_clustered
        for x in clusterer.labels_
    ]
    # fig, axs = plt.subplots(1, 3)
    # axs[0].scatter(pos.iloc[:, 0], pos.iloc[:, 1], c=cluster_colors, s=50)
    # axs[1].scatter(pos.iloc[:, 1], pos.iloc[:, 2], c=cluster_colors, s=50)
    # axs[2].scatter(pos.iloc[:, 0], pos.iloc[:, 2], c=cluster_colors, s=50)
    # plt.show()
    # exit()
    to_color = pd.Series(cluster_colors, index=to_color.index)
    return to_color, clusterer.labels_


def model_varaibles(fm, pos, min_cs, eps):
    from matplotlib import pyplot as plt
    import hdbscan

    clusters = []
    coverage = []

    x_axis = "min_sample"
    for var in np.linspace(2, 102, 100, dtype=int):
        var = int(var)
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cs,
            cluster_selection_method="leaf",
            cluster_selection_epsilon=eps,
            min_samples=var,
        )
        clusterer.fit_predict(pos)
        labels = clusterer.labels_
        cluster_labels = [x for x in labels if x >= 0]
        labels = set(cluster_labels)
        coverage.append((var, len(labels) / fm.shape[1]))
        clusters.append((var, len(labels)))

    fig, axs = plt.subplots(1, 2)
    axs[0].plot(*zip(*clusters))
    axs[0].set_title("Clusters")
    axs[0].set_ylabel("Cluster count")
    axs[0].set_xlabel(x_axis)
    axs[1].plot(*zip(*coverage))
    axs[1].set_title("Coverage")
    axs[1].set_ylabel("Coverage")
    axs[1].set_xlabel(x_axis)

    plt.show()
    exit()


def feature_coloring(to_color, feature_matrix, category):
    used_colors = set()
    for idx, term in enumerate(category.index):
        # check if any coloring necessary
        needs_color = to_color.isna()
        if not needs_color.any():
            st.log.debug("All colors are set...")
            break

        term_data = feature_matrix[term]
        if not term_data.any():
            continue

        # color = color_pallette[idx % len(colors)]
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

    return to_color


def get_color(used_colors: set):
    """Get a random color that is not in used_colors"""
    while True:
        color = np.random.randint(0, 255, 3)
        hex = "#{:02x}{:02x}{:02x}".format(*color)
        if hex not in used_colors:
            used_colors.add(hex)
            return color / 255, used_colors


def extract_pos(layout):

    pos = list(layout[["x", "y", "z"]].to_numpy())
    return pos


def get_cluster_labels(cluster, tax_id, cluster_dir, category):
    cluster["cluster"] = cluster["cluster"].fillna(-1)
    cluster = cluster.astype({"cluster": int})
    grouped = cluster.groupby("cluster")
    cluster = pd.DataFrame(index=grouped.groups.keys())
    for_request = cluster.copy()

    cluster["member"] = grouped.apply(lambda x: list(x.index)).values
    cluster["member"] = cluster["member"].apply(lambda x: ",".join(str(i) for i in x))
    for_request["member"] = grouped[ST.stringdb_identifier].apply(lambda x: ",".join(x))
    cluster_names = rfe.main(for_request, tax_id, cluster_dir, category)

    cluster.index = [cluster_names.get(x, x) for x in cluster.index]
    return cluster


def recolor(
    _dir, clean_name, organism, tax_id, functional_threshold, eps, preview_layout
):
    organism_dir = os.path.join(_dir, clean_name)
    node_colors = data_io.read_node_layouts(_dir, clean_name)
    nodes = data_io.read_nodes_pickle(_dir, clean_name)
    identifiers = nodes[ST.stringdb_identifier].copy()
    functional_annotations = fa.get_annotations(_dir, clean_name, tax_id)
    feature_matrices = fa.get_feature_matrices(
        _dir, clean_name, identifiers, functional_threshold=functional_threshold
    )

    # for feature_name, feature_matrix in feature_matrices.items():
    #     print(feature_name)
    #     print("=" * 50)
    #     print(feature_matrix)
    for layout, nodes in node_colors.items():
        # print(layout)
        # print("=" * 50)
        # print(nodes)
        if layout not in feature_matrices:
            st.log.debug(f"Layout {layout} not in feature matrices.")
            continue
        if layout not in functional_annotations:
            st.log.debug(f"Layout {layout} not in functional annotations.")
            continue
        feature_matrix = feature_matrices[layout]
        category = functional_annotations[layout]

        if feature_matrix is None:
            continue
        pos = extract_pos(nodes)
        nodes[["r", "g", "b", "a", "cluster"]] = color_layout(
            len(nodes),
            "functional",
            category,
            feature_matrix,
            pos=pos,
            eps=eps,
            preview_layout=preview_layout,
        )
        cluster = pd.concat([identifiers, nodes.cluster], axis=1)
        nodes = nodes.drop(columns=["cluster"]).copy()
        data_io.write_node_csv(organism_dir, organism, layout, nodes, True)
        data_io.write_cluster_information(organism_dir, organism, layout, cluster, True)
