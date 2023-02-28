import glob
import json
import os
import shutil

import numpy as np
import pandas as pd
import requests
from goatools import obo_parser

import src.settings as st
from interactomes.read_string import prepare_feature_matrices, read_network
from src.classes import Evidences
from src.classes import NodeTags as NT
from src.classes import Organisms
from src.layouter import Layouter


def upload(
    directory: str,
    src: str,
    ip: str = "localhost",
    port: int = 5000,
    annotations_threshold: float = 0.01,
    max_num_features: int = 100,
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
    print(f"Uploading network for {organism} with tax_id {tax_id}.")
    annot_file = os.path.join(src_dir, f"{tax_id}.gaf.gz")
    ont_file = os.path.join(src, "go-basic.obo")
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

        # # Move network.json.gzip to project folder
        # unfiltered_annotations = {}
        # for file in os.listdir(f"{src_dir}/functional_annotations"):
        #     if not file.endswith(".pickle"):
        #         continue
        #     if file.endswith("_filtered.pickle"):
        #         unfiltered_annotations[file.strip("_filtered.pickle")] = pd.read_pickle(
        #             f"{src_dir}/functional_annotations/{file}"
        #         )

        # # Write GO terms to nodes.json
        # nodes_json = os.path.join(target_dir, "nodes.json")
        # with open(nodes_json, "r") as f:
        #     nodes_data = json.load(f)
        #     nodes_data = pd.DataFrame(nodes_data["nodes"])

        # nodes, links, functional_annotations = read_network(directory, src, True)

        # functional_annotations = dict(
        #     sorted(
        #         functional_annotations.items(), key=lambda x: x[1].size, reverse=True
        #     )[:max_num_features]
        # )
        # categories = list(functional_annotations.keys())
        # identifiers = nodes[NT.identifier].copy()
        # feature_matrices = prepare_feature_matrices(
        #     "",
        #     functional_annotations,
        #     annotations_threshold,
        #     max_num_features,
        #     identifiers,
        #     categories,
        # )[2]
        # all_features = pd.concat(feature_matrices, axis=1)

        # lengths = all_features.swifter.apply(lambda x: x.sum())
        # lengths = {
        #     k: v
        #     for k, v in sorted(lengths.items(), key=lambda item: item[1], reverse=True)[
        #         :max_num_features
        #     ]
        # }
        # all_features = all_features[[c for c in lengths]]

        # annot, ont = read_go_annotation(annot_file, ont_file)

        # new_names = {}
        # nodes = pd.concat([nodes, all_features], axis=1)

        # go_columns = [c for c in all_features.columns if c.startswith("GO:")]

        # def handel_term(x, entries, col):
        #     row = entries[entries["go"] == col]
        #     if row.empty:
        #         return x
        #     qualifers = row.get("qualifier")
        #     if qualifers is None or qualifers.empty:
        #         return x
        #     x[col] = qualifers.values[0]
        #     return x

        # def set_qualifiers(
        #     x, identifier, annot: pd.core.groupby.generic.DataFrameGroupBy, go_columns
        # ):
        #     if x[identifier] not in annot.groups:
        #         return x
        #     entries = annot.get_group(x[identifier])
        #     #TODO THROWS VALUE ERROR SOMETIMES (WHY?)
        #     try:
        #         to_handle = [c for c in go_columns if c in x.index and x[c]]
        #     except ValueError as e:
        #         st.log.debug(e)
        #         st.log.debug(x)
        #         exit()
        #     for col in to_handle:
        #         x = handel_term(x, entries, col)
        #     return x

        # annot_gene = annot.groupby(NT.gene_name)

        # nodes = nodes.swifter.apply(
        #     set_qualifiers,
        #     axis=1,
        #     args=(
        #         NT.gene_name,
        #         annot_gene,
        #         go_columns,
        #     ),
        # )
        # for col in go_columns:
        #     if col in ont:
        #         new_names[col] = f"{ont[col].name};{col}"
        #     else:
        #         st.log.error(f"Could not find {col} in ontology.")
        # nodes = nodes.rename(columns=new_names)

        # nodes = nodes.to_json(orient="records")
        # links = links.to_json(orient="records")

        # files.append(("nodes_data", nodes))
        # files.append(("links_data", links))

        # r = requests.post(
        #     f"http://{ip}:{port}/StringEx/receiveInteractome?project_name={directory}",
        #     files=files,
        # )
        # st.log.info(f"Uploaded network for {organism} as project {directory}.")
        # st.log.debug(f"Response: {r}")
        ...
    except requests.exceptions.ConnectionError as e:
        st.log.error(f"Could not connect to {ip}:{port}. Upload failed.")
        print(e)


def read_go_annotation(annot_file, ont_file):
    """Reads the annotation file and returns a dictionary with the annotations."""
    annot = pd.read_table(annot_file, comment="!", header=None, sep="\t")
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
