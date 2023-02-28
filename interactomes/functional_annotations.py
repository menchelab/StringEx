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
# Adapted based on https://string-db.org/cgi/help?sessionId=bsMEwNSWdi3y
##############################################################
import json
import os

import pandas as pd
import requests  # # python -m pip install requests

from src.settings import log


def get_annotations(
    # taxid: str,
    # _dir: str,
    # n: int,
    # threshold: float,
    # get_unfiltered: bool = False,
    # unfiltered_threshold: float = 0,
    df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Extracts all functional annotations for a given organism with a percentage of members above a given threshold.

    Args:
        taxid (str): taxonomy id of the organism.
        _dir (str): directory where the annotations are stored.
        n (int): number of proteins in the organism.
        threshold (float): percentage of members above which the annotation is considered.

    Returns:
        dict[str, pd.DataFrame]: dictionary of functional annotations.
    """
    # file_path = os.path.join(_dir, f"{taxid}.protein.enrichment.terms.v11.5.txt")
    # with open(file_path, "r") as f:
    #     df = pd.read_csv(f, sep="\t")
    categories = df["category"].unique().tolist()
    # if not get_unfiltered:
    #     categories = [
    #         cat for cat in categories if df[df["category"] == cat].size / n > threshold
    #     ]
    #     df = df.drop(df[~df["category"].isin(categories)].index)
    terms = df["term"].unique().tolist()

    # def filter_out_terms(df, threshold):
    #     return (
    #         df.groupby("term")
    #         .filter(lambda x: x.size / n > threshold)["term"]
    #         .unique()
    #         .tolist()
    #     )

    # if get_unfiltered:
    #     unfiltered_annotations = {}
    #     terms = filter_out_terms(df, unfiltered_threshold)
    # else:
    #     terms = filter_out_terms(df, threshold)
    # df = df[df["term"].isin(terms)].copy()
    # def handle_term(term_frame):
    #     members = term_frame["#string_protein_id"].unique().tolist()
    #     number_of_members = len(members)
    #     if number_of_members / n < threshold and not get_unfiltered:
    #         return None
    #     description = term_frame["description"].unique().tolist()[0]
    #     res = {
    #         "members": members,
    #         "description": description,
    #         "number_of_members": number_of_members,
    #     }
    #     return res

    # collection = df.swifter.groupby(["category", "term"]).apply(handle_term)
    functional_annotations = {}

    categories = df.groupby("category")
    for cat in categories.groups:
        log.debug(f"Processing {cat}", flush=True)
        terms = categories.get_group(cat).groupby("term")
        collection = {}
        for term in terms.groups.keys():
            term_frame = terms.get_group(term).copy()
            members = term_frame["#string_protein_id"].unique().tolist()
            number_of_members = len(members)
            # if number_of_members / n < threshold and not get_unfiltered:
            #     continue
            # if number_of_members / n < unfiltered_threshold and get_unfiltered:
            #     continue
            description = term_frame["description"].unique().tolist()[0]
            res = {
                "members": members,
                "description": description,
                "number_of_members": number_of_members,
            }
            collection[term] = res

        collection = pd.DataFrame(collection).T
        collection = collection.dropna()
        if collection.empty:
            continue
        collection = collection.sort_values(by="number_of_members", ascending=False)
        # if get_unfiltered:
        #     unfiltered_annotations[cat] = collection.copy()
        # collection = collection[collection["number_of_members"] / n > threshold]
        # if collection.empty:
        #     continue
        functional_annotations[cat] = collection

    # if get_unfiltered:
    #     unfiltered_annotations = dict(
    #         sorted(
    #             unfiltered_annotations.items(), key=lambda x: x[1].size, reverse=True
    #         )
    #     )
    log.debug(f"Filtered {len(functional_annotations)}")
    # log.debug(f"Unfiltered {len(unfiltered_annotations)}")
    return functional_annotations  # , unfiltered_annotations
