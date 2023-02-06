import gzip
import os

import requests


def download(tax_id: int, dest: str, clean_name: str, string_db_ver: str = "11.5"):
    """Used to download necessary files from STRING database to create full genome networks.

    Args:
        tax_id (int): Taxonomy ID of the organism.
        organism (str): Organism for which the data should be downloaded.
        dest (str): Destination folder for the downloaded files.
    """
    url = "https://stringdb-static.org/download/"
    links = f"protein.links.detailed.v{string_db_ver}/"
    info = f"protein.info.v{string_db_ver}/"
    ali = f"protein.aliases.v{string_db_ver}/"
    organism_links = f"{tax_id}.{links[:-1]}.txt.gz"
    organism_info = f"{tax_id}.{info[:-1]}.txt.gz"
    organism_aliases = f"{tax_id}.{ali[:-1]}.txt.gz"
    directory = os.path.join(dest, clean_name)
    os.makedirs(directory, exist_ok=True)
    for data, file in zip(
        [links, info, ali],
        [organism_links, organism_info, organism_aliases],
    ):
        if not os.path.exists(os.path.join(directory, file)):
            r = requests.get(url + data + file)
            with open(os.path.join(directory,file), "wb+") as f:
                f.write(r.content)


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
