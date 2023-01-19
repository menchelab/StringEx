import glob
import gzip
import os
import sys
from ast import alias

import pandas
import requests

from src import settings as st


def download(tax_id: int, organism: str, dest:str,clean_name:str):
    """Used to download necessary files from STRING database to create full genome networks.

    Args:
        tax_id (int): Taxonomy ID of the organism.
        organism (str): Organism for which the data should be downloaded.
        dest (str): Destination folder for the downloaded files.
    """
    url = "https://stringdb-static.org/download/"
    links = "protein.links.detailed.v11.5/"
    info = "protein.info.v11.5/"
    ali = "protein.aliases.v11.5/"
    organism_links = f"{tax_id}.protein.links.detailed.v11.5.txt.gz"
    organism_info = f"{tax_id}.protein.info.v11.5.txt.gz"
    organism_aliases = f"{tax_id}.protein.aliases.v11.5.txt.gz"
    directory = os.path.join(dest, clean_name)
    os.makedirs(directory, exist_ok=True)
    for data, file in zip(
        [links, info, ali],
        [organism_links, organism_info, organism_aliases],
    ):
        if not os.path.exists(os.path.join(directory, file.strip(".gz"))):
            print(url + data + file)
            r = requests.get(url + data + file)
            content = gzip.decompress(r.content)
            with open(os.path.join(directory, file.strip(".gz")), "wb+") as f:
                f.write(content)

def filter_entries(tax_id:int, organism:str,dest:str,clean_name:str):
    for file in glob.glob(os.path.join(dest, "*")):
        if file.endswith("protein.links.detailed.v11.5.txt"):
            link_file = file
        elif file.endswith(".protein.aliases.v11.5.txt"):
            alias_file = file
        elif file.endswith(".protein.info.v11.5.txt"):
            description_file = file
    alias_table = pandas.read_table(
        alias_file,
        header=0,
        sep="\t",
        index_col=0,
    )

    # TODO: Filter unused lines
    
if __name__ == "__main__":
    organisms = {
        "human": 9606,
        "mouse": 10090,
        "rat": 10116,
        "zebrafish": 7955,
        "fly": 7227,
        "worm": 6239,
        "yeast": 4932,
        "ecoli": 362663,
        "arabidopsis": 3702,
    }
    for organism, tax_id in organisms.items():
        download(tax_id, organism)
