import json
import os

import flask
import GlobalData as GD
from flask_socketio import emit
from PIL import Image
import py4cytoscape as p4c

import uploader

from . import settings as st
from . import util as string_util
from . import workflows as wf
from . import routes
import util
import requests

from io_blueprint import IOBlueprint

url_prefix = "/StringEx"

blueprint = IOBlueprint(
    "StringEx",
    __name__,
    url_prefix=url_prefix,
    template_folder=st._THIS_EXT_TEMPLATE_PATH,
    static_folder=st._THIS_EXT_STATIC_PATH,
)

main_tabs = ["string_main_tab.html", "string_send_subset.html"]
upload_tabs = ["string_upload_tab.html", "string_map_tab.html"]


@blueprint.before_app_first_request
def stringex_setup():
    string_util.pepare_uploader()
    string_util.move_on_boot()


@blueprint.route("/preview", methods=["GET"])
def string_preview():
    """Route to STRING WEBGL Preview. If No project is selected, redirect to the project selection page of the StringEx WEBGL preview. this function is based on the preview function of base VRNetzer app.py."""
    return routes.preview()


@blueprint.route("/uploadfiles", methods=["GET", "POST"])
def string_ex_upload_files() -> str:
    """This route is used to upload a VRNetz using the STRING Uploader. A POST request is send to it, when a user clicks the "upload" button.

    Returns:
        str: A status giving information whether the upload was successful or not.
    """
    # TODO: allow to use provided layout
    return routes.upload_files()


@blueprint.route("/mapfiles", methods=["GET", "POST"])
def string_ex_map_files():
    """This route is used to map a small VRNetz onto full genome STRING interactomes. A POST request is send to it, when a user clicks the "map" button.
    Returns:
        str: A status giving information whether the upload was successful or not.
    """
    return routes.map_files()


@blueprint.route("/receiveNetwork", methods=["POST"])
def string_ex_receive_network_json():
    receiveNetwork = flask.request.get_json()
    wf.VRNetzer_send_network_workflow(receiveNetwork, blueprint)
    project = receiveNetwork["form"]["project"]
    return json.dumps({"url": f"/StringEx/resultPage/{project}"})


@blueprint.route("/resultPage/<project>", methods=["GET"])
def string_ex_result_page(project):
    """Route to the results page project depended."""
    username = util.generate_username()
    layouts = ""
    flask.session["username"] = username
    flask.session["room"] = 1
    project_path = os.path.join(st._PROJECTS_PATH, project, "pfile.json")
    with open(project_path, "r") as f:
        pfile = json.load(f)
    return flask.render_template(
        "string_send_result_page.html",
        project=project,
        layouts=layouts,
        pfile=pfile,
        pdata=json.dumps(pfile),
        sessionData=json.dumps(GD.sessionData),
    )


@blueprint.on(
    "send_to_cytoscape",
)
def string_ex_get_selection(message):

    """Get the selected Nodes of the current open network. and provide it as a raw tab separated is of edges"""
    selected = GD.sessionData["selected"]
    if len(selected) == 0:
        selected = None
    project = GD.sessionData["actPro"]
    ip = flask.request.remote_addr
    port = 1234
    user = message.get("user", util.generate_username())
    layout = message.get("layout", "")
    color = message.get("color", "")
    title = f"{layout} & {color}"
    base_url = "http://" + str(ip) + f":{port}/v1"

    try:
        p4c.cytoscape_ping(base_url=base_url)
    except requests.exceptions.RequestException:
        blueprint.emit(
            "status",
            {
                "message": f"Could not connect to Cytoscape at {base_url}. Please check if Cytoscape is running and if the url is correct. Is cyREST installed?",
                "status": "error",
            },
        )
        return
    nodes, selected = string_util.extract_node_data(selected, project, layout, color)
    links = string_util.extract_link_data(selected, project)
    st.log.debug("Extracted node and link data")

    # Create network
    suid = p4c.create_network_from_data_frames(
        nodes, links, base_url=base_url, collection=project, title=title
    )
    st.log.debug(f"Created network with SUID: {suid}")

    # Create style
    style = "VRNetzer_Style"
    if style not in p4c.get_visual_style_names(base_url=base_url):
        p4c.create_visual_style(style, base_url=base_url)
        st.log.debug(f"Created style: {style}")

    # Set colors
    p4c.set_node_color_mapping(
        table_column="color", mapping_type="p", style_name=style, base_url=base_url
    )
    st.log.debug(f"Set node color mapping")

    # Set layout
    cords = ["x", "y"]
    properties = ["NODE_X_LOCATION", "NODE_Y_LOCATION"]
    if "NODE_Z_LOCATION" in p4c.get_visual_property_names():
        cords.append("z")
        properties.append("NODE_Z_LOCATION")

    for property, column in zip(properties, cords):
        mapping = p4c.map_visual_property(
            property, table_column=column, mapping_type="p", base_url=base_url
        )
        p4c.update_style_mapping(style, mapping, base_url=base_url)
        st.log.debug(f"Set {property} mapping")

    # Set style
    p4c.set_visual_style(style, base_url=base_url)
    st.log.debug(f"Set style: {style}")

    # Fit content
    p4c.fit_content(base_url=base_url)
    st.log.debug(f"Fit content")

    blueprint.emit(
        "status",
        {
            "message": f"Project {project} successfully send to Cytoscape.",
            "status": "success",
        },
    )
    st.log.debug(f"Created new network in Cytoscape at client {ip}:{port}")


@blueprint.on("delete")
def string_ex_delete_all_networks():
    p4c.delete_network()
