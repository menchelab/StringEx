import json
import os
import pandas as pd
import requests

import src.settings as st
from interactomes import data_io
from interactomes import functional_annotations as fa
from src.classes import NodeTags as NT
from src.classes import Organisms
from src.classes import StringTags as ST


def upload(
    directory: str,
    src: str,
    ip: str = "localhost",
    port: int = 5000,
    annotations_threshold: float = 0.1,
    max_num_features: int = 100,
    no_upload=False,
) -> None:
    """Uploads the network using the internal upload route of the VRNetzer.

    Args:
        directory (str): directory in which the layout files are located.
        ip (str): IP of the VRNetzer.
        port (int): Port of the VRNetzer.
        src (str): path directory, where the csv files are located.
    """
    layouts = []
    link_layouts = []
    src_dir = os.path.join(src, directory)
    organism = Organisms.get_organism_name(directory)
    tax_id = Organisms.get_tax_ids(organism)
    st.log.info(f"Uploading network for {organism} with tax_id {tax_id}.")
    annot_file = os.path.join(src_dir, f"{tax_id}.gaf.gz")
    ont_file = os.path.join(src, "go-basic.obo")
    keyword_file = os.path.join(src, "uniprot_keywords.tsv.gz")
    target_dir = os.path.join(st._PROJECTS_PATH, directory)
    nodes_dir = os.path.join(src_dir, "nodes")
    links_dir = os.path.join(src_dir, "links")
    layouts = [os.path.join(nodes_dir, file) for file in os.listdir(nodes_dir)]
    link_layouts = [os.path.join(links_dir, file) for file in os.listdir(links_dir)]
    for link_layout in link_layouts:
        if link_layout.endswith("any.csv"):
            tmp = link_layout
            link_layouts.remove(link_layout)
            link_layouts.append(tmp)
            break

    files = []
    for file in layouts:
        files.append(("layouts", open(file, "rb")))
    for file in link_layouts:
        files.append(("links", open(file, "rb")))
    data = {"namespace": "New", "new_name": directory}

    try:
        if not no_upload:
            r = requests.post(f"http://{ip}:{port}/delpro?project={directory}")
            r = requests.post(f"http://{ip}:{port}/uploadfiles", data=data, files=files)
            st.log.info(
                f"Trying to upload network for {organism} as project {directory}.",
                flush=True,
            )
    except requests.exceptions.ConnectionError:
        st.log.error(f"Could not connect to {ip}:{port}. Upload failed.", flush=True)
        return

    try:
        r = requests.get(f"http://{ip}:{port}/StringEx/status")
        st.log.debug(r)
        if r.status_code != 200:
            raise requests.exceptions.ConnectionError
    except requests.exceptions.ConnectionError:
        st.log.error(
            f"Could not connect to VRNetzer at {ip}:{port}. Is StringEx installed and is the Server running?",
            flush=True,
        )
        return

    try:

        # Write GO terms to nodes.json
        nodes_json = os.path.join(target_dir, "nodes.json")
        with open(nodes_json, "r") as f:
            nodes_data = json.load(f)
            nodes_data = pd.DataFrame(nodes_data["nodes"])

        nodes, links, functional_annotations = data_io.read_network(
            src, directory, True
        )

        functional_annotations = dict(
            sorted(
                functional_annotations.items(), key=lambda x: x[1].size, reverse=True
            )[:max_num_features]
        )
        identifiers = nodes[ST.stringdb_identifier].copy()
        fm_dict = fa.get_feature_matrices(
            src,
            directory,
            identifiers,
            functional_annotations,
            annotations_threshold,
            reconstruct=False,
        )
        feature_matrices = list(fm_dict.values())

        all_features = pd.concat(feature_matrices, axis=1)

        lengths = all_features.swifter.apply(lambda x: x.sum())
        # Filter categories based on total coverage => percent of node covered by this category
        lengths = {
            k: v
            for k, v in sorted(lengths.items(), key=lambda item: item[1], reverse=True)[
                :max_num_features
            ]
        }
        to_add = set([c for c in lengths])
        all_features = all_features[to_add].copy()

        # If a feature is present twice, just say its true if in any
        all_features = all_features.groupby(all_features.columns, axis=1).apply(
            lambda x: x.any(axis=1)
        )

        annot, ont = data_io.read_go_annotation(annot_file, ont_file)
        uniprot_keywords = data_io.read_uniprot_keywords(keyword_file)

        nodes = pd.concat([nodes, all_features], axis=1)

        go_columns = [c for c in all_features.columns if c.startswith("GO:")]

        annot_gene = annot.groupby(NT.gene_name)

        def handle_row(x, identifier, annot, go_columns):
            annot_entries = annot.get_group(x[identifier])
            for term in go_columns:
                entries = annot_entries[annot_entries["go"] == term]
                if entries.empty:
                    continue
                qualifiers = entries.get("qualifier")
                if qualifiers is None or qualifiers.empty:
                    continue
                x[term] = qualifiers.values[0]
            return x

        has_gene_name = nodes[NT.gene_name].notna() & nodes[NT.gene_name].isin(
            annot_gene.groups
        )
        has_gene_name = nodes[has_gene_name].copy()
        has_gene_name = has_gene_name[[NT.gene_name] + go_columns].swifter.apply(
            handle_row,
            axis=1,
            args=(
                NT.gene_name,
                annot_gene,
                go_columns,
            ),
        )

        new_names = {}
        for col in go_columns:
            if col in ont:
                new_names[col] = f"{ont[col].name};{col}"
            else:
                st.log.error(f"Could not find {col} in ontology.")
        uniprot_column = [c for c in all_features.columns if c.startswith("KW-")]
        for col in uniprot_column:
            if col in uniprot_keywords.index:
                new_names[col] = f"{uniprot_keywords.at[col,'Name']};{col}"
            else:
                st.log.error(f"Could not find {col} in uniprot keywords.")
        features = list(fm_dict.keys())
        while True:
            clusters = data_io.read_cluster_information(src_dir, features.pop())
            if clusters is not None:
                break
        cluster_labels = []
        clusters["member"] = clusters["member"].apply(
            lambda x: [int(x) for x in x.split(",")]
        )
        for idx, row in clusters.iterrows():
            if str(idx) == "-1":
                continue
            cluster_labels.append({"name": idx, "nodes": list(row.values)})

        nodes = nodes.rename(columns=new_names)
        nodes.update(has_gene_name)

        nodes["id"] = nodes.index
        links["id"] = links.index

        nodes = nodes.to_json(orient="records")
        links = links.to_json(orient="records")

        files.append(("nodes_data", nodes))
        files.append(("links_data", links))

        files.append(("cluster_labels", json.dumps(cluster_labels)))

        r = requests.post(
            f"http://{ip}:{port}/StringEx/receiveInteractome?project_name={directory}",
            files=files,
        )
        st.log.info(f"Uploaded network for {organism} as project {directory}.")
        st.log.debug(f"Response: {r}")
        ...
    except requests.exceptions.ConnectionError as e:
        st.log.error(f"Could not connect to {ip}:{port}. Upload failed.")
        print(e)


def read_uniprot_keywords(keyword_file):
    pass
