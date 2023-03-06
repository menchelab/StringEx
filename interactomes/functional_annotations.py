import pandas as pd
import os
from src.settings import log
from interactomes import data_io
from src.classes import Organisms

FUNCTIONAL_CATEGORIES = [
    # "Protein Domains (Pfam)",
    "Biological Process (Gene Ontology)",
    "Molecular Function (Gene Ontology)",
    "Annotated Keywords (UniProt)",
    "Cellular Component (Gene Ontology)",
    "Disease-gene associations (DISEASES)",
    "Tissue expression (TISSUES)",
    "Subcellular localization (COMPARTMENTS)",
]


def get_annotations(
    _dir: str = None,
    organism: str = None,
    tax_id: str = None,
    df: pd.DataFrame = None,
    reconstruct: bool = False,
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
    if _dir and organism:
        organism_dir = os.path.join(_dir, organism)
    if df is None:

        if _dir is None:
            raise ValueError("Either a dataframe or a directory must be provided")

        if tax_id is None:
            raise ValueError("tax_id must be provided")

        organism_dir = os.path.join(_dir, organism)
        df = data_io.read_enrichment_terms(organism_dir, tax_id)

    if not reconstruct:
        if os.path.exists(os.path.join(_dir, organism, "functional_annotations")):
            return data_io.read_functional_annotations(_dir, organism)

    categories = df["category"].unique().tolist()
    terms = df["term"].unique().tolist()

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
            if number_of_members == 1:
                continue
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

        functional_annotations[cat] = collection
    log.debug(f"Filtered {len(functional_annotations)}")
    if organism_dir:
        organism_dir
        data_io.write_functional_annotations(organism_dir, functional_annotations)
    return functional_annotations


def prepare_feature_matrices(
    name,
    functional_annotations,
    functional_threshold,
    layout,
    identifiers,
    _dir,
    clean_name,
    functional_categories=FUNCTIONAL_CATEGORIES,
):
    new_algos = []
    new_names = []

    fms, functional_annotations = construct_feature_matrices(
        name,
        functional_annotations,
        identifiers,
        functional_categories=functional_categories,
    )

    data_io.write_feature_matrices(_dir, clean_name, fms)
    for name, fm in fms.items():
        new_algos.append(layout)
        new_names.append(name)
        fm = fm.T
        fms[name] = fm[fm.sum(axis=1) / len(identifiers) > functional_threshold].T

    return (
        new_algos,
        new_names,
        fms,
        functional_annotations,
    )


def get_feature_matrices(
    _dir,
    clean_name,
    identifiers,
    functional_annotations=None,
    functional_threshold=0.01,
    functional_categories=FUNCTIONAL_CATEGORIES,
    reconstruct=False,
):

    if not reconstruct:
        if os.path.exists(
            os.path.join(_dir, clean_name, "functional_annotations", "fm")
        ):
            fms = data_io.read_feature_matrices(
                _dir, clean_name, len(identifiers), functional_threshold
            )
            if not len(fms) == 0:
                return fms

    if functional_annotations is None:
        tax_id = Organisms.get_tax_ids(directory=clean_name)
        functional_annotations = get_annotations(_dir, clean_name, tax_id, reconstruct)
    fms = construct_feature_matrices(
        "",
        functional_annotations,
        identifiers,
        functional_categories=functional_categories,
        min_threshold=functional_threshold,
    )[0]
    data_io.write_feature_matrices(_dir, clean_name, fms)
    for name, fm in fms.items():
        fm = fm.T
        fms[name] = fm[fm.sum(axis=1) / len(identifiers) > functional_threshold].T
    return fms


def construct_feature_matrices(
    name,
    functional_annotations,
    identifiers,
    functional_categories=FUNCTIONAL_CATEGORIES,
    min_threshold=0.01,
):
    feature_matrices = {}
    filtered_functional_annotations = {}
    for cat in functional_annotations:
        category = functional_annotations[cat].copy()
        if functional_categories is not None and cat not in functional_categories:
            log.debug(
                f"Category {cat} is not a valid functional category. Consider adding it as its seems to be relevant."
            )
            continue
        category = category[
            category["number_of_members"] / len(identifiers) >= min_threshold
        ]
        if category.empty:
            continue
        log.debug(f"Mapping terms of category {cat} to nodes...", flush=True)
        feature_matrix = category.swifter.apply(
            lambda x: identifiers.isin(x.members), axis=1
        )
        feature_matrix = feature_matrix[feature_matrix.sum(axis=1) > 1]

        n = f"{name}{cat}"
        feature_matrix = feature_matrix.T
        feature_matrices[n] = feature_matrix
        filtered_functional_annotations[cat] = category

    return feature_matrices, filtered_functional_annotations
