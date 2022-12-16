#!Python3
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import interactomes.load_files as load_files
import interactomes.read_string as read_string
from src import settings as st
from src import util
from src.classes import Organisms

f_handler = RotatingFileHandler(
    os.path.join("logs", "interactome_construction.log"),
    mode="a",
    maxBytes=5 * 1024 * 1024,
    backupCount=2,
    encoding=None,
    delay=0,
)
f_handler.setLevel(st.LOG_LEVEL)
f_handler.setFormatter(st._LOG_FORMAT)
st.log.addHandler(f_handler)


def main():
    """Main function to construct the node layout and link layout files which can be uploaded to the VRNetzer website. This is to reproduce the full interactome STRING networks from scratch."""
    for organism in Organisms.all_organisms:
        if organism not in [
            Organisms.yeast,
        ]:
            continue
        tax_id = Organisms.get_tax_ids(organism)
        st.log.info(f"Processing organism: {organism} with taxonomy id: {tax_id}.")
        # load_files.download(tax_id, organism)
        # read_string.construct_graph("STRING", organism)
        # read_string.construct_layouts(organism)


if __name__ == "__main__":
    main()
