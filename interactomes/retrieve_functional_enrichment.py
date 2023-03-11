#!/usr/bin/env python3

##############################################################
## The following script retrieves and prints out
## significantly enriched (FDR < 1%) GO Processes
## for the given set of proteins.
##
## Requires requests module:
## type "python -m pip install requests" in command line (win)
## or terminal (mac/linux) to install the module
##############################################################

import requests  ## python -m pip install requests
import json
import os
import pandas as pd

string_api_url = "https://version-11-5.string-db.org/api"
output_format = "json"
method = "enrichment"


def main(clusters, tax_id, cluster_dir, category):
    cluster_names = {}
    for idx, cluster in clusters.iterrows():
        if idx == -1:
            continue
        my_genes = cluster["member"].replace(",", "%0d")
        description = api_call(my_genes, tax_id, cluster_dir, category, idx)
        if description is not None:
            cluster_names[idx] = description
    return cluster_names


def write_cluster_labels(_dir, cluster_names, category):
    with open(os.path.join(_dir, "clusters", f"{category}_names.json"), "w") as f:
        json.dump(cluster_names, f)
    return cluster_names


def read_cluster_file(category):
    _dir = os.path.join(_dir, "clusters")
    file_name = os.path.join(_dir, f"{category}_cluster.csv")
    clusters = pd.read_csv(file_name, sep="\t", header=0, index_col=0)
    return clusters


def api_call(my_genes, species, cluster_dir, category, cluster):
    request_url = "/".join([string_api_url, output_format, method])

    ##
    ## Set parameters
    ##

    params = {
        "identifiers": my_genes,  # your protein
        "species": species,  # species NCBI identifier
        "caller_identity": "StringEx",  # your app name
    }

    ##
    ## Call STRING
    ##

    response = requests.post(request_url, data=params)

    ##
    ## Read and parse the results
    ##

    data = pd.read_json(response.text)
    if data.empty:
        return None
    path = os.path.join(
        cluster_dir,
        "enrichments",
        f"{category}",
        f"{cluster}_{category}_enrichment.csv",
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    categories = data["category"].unique()
    categories = [x for x in categories if x in category]
    data = data[data["category"].isin(categories)]
    data = data.sort_values(by="p_value")
    data = data[
        [
            "description",
            "p_value",
            "fdr",
            "number_of_genes",
            "number_of_genes_in_background",
            "inputGenes",
        ]
    ].copy()
    data.to_csv(path, index=False)
    if data.empty:
        return None
    return data["description"].values[0]


def open_result(file_name):
    data = pd.read_pickle(file_name)
    print(data.sort_values(by="p_value"))
    return data
