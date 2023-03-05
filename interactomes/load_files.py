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
    enrichment_terms = f"protein.enrichment.terms.v{string_db_ver}/"

    organism_links = f"{tax_id}.{links[:-1]}.txt.gz"
    organism_info = f"{tax_id}.{info[:-1]}.txt.gz"
    organism_aliases = f"{tax_id}.{ali[:-1]}.txt.gz"
    organism_enrichment_terms = f"{tax_id}.{enrichment_terms[:-1]}.txt.gz"
    directory = os.path.join(dest, clean_name)
    os.makedirs(directory, exist_ok=True)
    for data, file in zip(
        [links, info, ali, enrichment_terms],
        [organism_links, organism_info, organism_aliases, organism_enrichment_terms],
    ):
        if not os.path.exists(os.path.join(directory, file)):
            r = requests.get(url + data + file)
            with open(os.path.join(directory, file), "wb+") as f:
                f.write(r.content)


def gene_ontology_download(organism: str, dest: str, clean_name: str):

    if organism == Organisms.human:
        url = "http://geneontology.org/gene-associations/goa_human.gaf.gz"
        file = "goa_human.gaf.gz"
    else:
        files = {
            Organisms.human: "goa_human.gaf.gz",
            Organisms.mouse: "mgi.gaf.gz",
            Organisms.rat: "rgd.gaf.gz",
            Organisms.zebrafish: "zfin.gaf.gz",
            Organisms.arabidopsis: "tair.gaf.gz",
            Organisms.fly: "fb.gaf.gz",
            Organisms.worm: "wb.gaf.gz",
            Organisms.yeast: "sgd.gaf.gz",
            Organisms.ecoli: "ecocyc.gaf.gz",
        }
        base_url = "http://current.geneontology.org/annotations/"
        file = files[organism]
        url = base_url + file
    tax_id = Organisms.get_tax_ids(organism)
    file_name = f"{tax_id}.gaf.gz"
    directory = os.path.join(dest, clean_name)
    if not os.path.exists(os.path.join(directory, file_name)):
        r = requests.get(url)
        with open(os.path.join(directory, file_name), "wb+") as f:
            f.write(r.content)


def download_go_terms(dest: str):
    url = "http://purl.obolibrary.org/obo/go/go-basic.obo"
    r = requests.get(url)
    file_path = os.path.join(dest, "go-basic.obo")
    with open(file_path, "wb+") as f:
        f.write(r.content)


def download_uniprot_keywords(dest: str):
    url = "https://rest.uniprot.org/keywords/stream?compressed=true&download=true&fields=id%2Cname&format=tsv&query=*"
    r = requests.get(url)
    file_path = os.path.join(dest, "uniprot_keywords.tsv.gz")
    with open(file_path, "wb+") as f:
        f.write(r.content)


if __name__ == "__main__":

    class Organisms:
        human = "H.sapiens"
        mouse = "M.musculus"
        yeast = "S.cerevisiae"
        worm = "C.elegans"
        fly = "D.melanogaster"
        arabidopsis = "A.thaliana"
        zebrafish = "D.rerio"
        rat = "R.norvegicus"
        ecoli = "E.coli"
        all_organisms = sorted(
            [human, mouse, yeast, worm, fly, arabidopsis, zebrafish, rat, ecoli]
        )

        @staticmethod
        def get_tax_ids(organism: str) -> int:
            """Return the tax id for the organism.

            Args:
                organism (str): organism for which the tax id is needed

            Returns:
                int: taxanomy id of the organism
            """
            tax_ids = {
                Organisms.human: 9606,
                Organisms.mouse: 10090,
                Organisms.rat: 10116,
                Organisms.zebrafish: 7955,
                Organisms.fly: 7227,
                Organisms.worm: 6239,
                Organisms.yeast: 4932,
                Organisms.ecoli: 362663,
                Organisms.arabidopsis: 3702,
            }
            return tax_ids.get(organism)

        @staticmethod
        def get_scientific_name(organism: str) -> str:
            """Return the tax id for the organism.

            Args:
                organism (str): organism for which the scientific name is needed

            Returns:
                str: Scientific name of the organism.
            """
            tax_ids = {
                Organisms.human: "Homo sapiens",
                Organisms.mouse: "Mus musculus",
                Organisms.rat: "Rattus norvegicus",
                Organisms.zebrafish: "Danio rerio",
                Organisms.fly: "Drosophila melanogaster",
                Organisms.worm: "Caenorhabditis elegans",
                Organisms.yeast: "Saccharomyces cerevisiae",
                Organisms.ecoli: "Escherichia coli 536",
                Organisms.arabidopsis: "Arabidopsis thaliana",
            }
            return tax_ids.get(organism)

        @staticmethod
        def get_file_name(organism: str) -> str:
            """Return the project name for the desired organism.

            Args:
                organism (str): organism for which the project name is needed

            Returns:
                str: name of the project
            """
            file_names = {
                Organisms.human: "string_human_ppi",
                Organisms.mouse: "string_mouse_ppi",
                Organisms.yeast: "string_yeast_ppi",
                Organisms.worm: "string_worm_ppi",
                Organisms.fly: "string_fly_ppi",
                Organisms.arabidopsis: "string_arabidopsis_ppi",
                Organisms.zebrafish: "string_zebrafish_ppi",
                Organisms.rat: "string_rat_ppi",
                Organisms.ecoli: "string_ecoli_ppi",
            }
            return file_names.get(organism)

    organisms = {
        Organisms.human: 9606,
        Organisms.mouse: 10090,
        Organisms.rat: 10116,
        Organisms.zebrafish: 7955,
        Organisms.fly: 7227,
        Organisms.worm: 6239,
        Organisms.yeast: 4932,
        Organisms.ecoli: 362663,
        Organisms.arabidopsis: 3702,
    }
    for organism, tax_id in organisms.items():
        # download(tax_id, organism)
        gene_ontology_download(
            organism, "string_interactomes", Organisms.get_file_name(organism)
        )
else:
    from src.classes import Organisms
