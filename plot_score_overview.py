import os

import numpy as np
import pandas
from matplotlib import pyplot as plt

from src.classes import Organisms


def extract_score(networks_directory, organism, string_db_ver="11.5"):
    clean_name = Organisms.get_file_name(organism)
    tax_id = Organisms.get_tax_ids(organism)
    directory = os.path.join(networks_directory, clean_name)
    file = os.path.join(
        directory, f"{tax_id}.protein.links.detailed.v{string_db_ver}.txt"
    )
    network_table = pandas.read_table(file, header=0, sep=" ")
    scores = network_table["combined_score"]
    mean = np.mean(scores)
    std = np.std(scores)
    fig, axs = plt.subplots(1, 2)
    axs[0].hist(scores, bins=100)
    axs[1].boxplot(scores)
    axs[0].annotate(f"Mean: {mean}\nSD: {std}", (600, 50000))
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    extract_score("string_interactomes", Organisms.ecoli)
