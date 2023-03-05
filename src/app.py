import json
import multiprocessing as mp
import os

import flask
import GlobalData as GD
from io_blueprint import IOBlueprint

import util

from . import routes
from . import settings as st
from . import util as string_util
from . import workflows as wf
from .send_to_cytoscape import send_to_cytoscape

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


@blueprint.route("/")
def string_ex_index():
    """Route to the index page."""
    return flask.redirect("/")


@blueprint.route("/receiveInteractome", methods=["POST"])
def string_ex_receive_interactome():
    """Route to receive the interactome from prepared by a client using the the provided script"""
    data = {"project_name": flask.request.args.get("project_name")}
    files = flask.request.files
    data["host"] = flask.request.host
    res = routes.receive_interactome(data, files)
    if hasattr(GD, "annotationScraper"):
        GD.annotationScraper.update_annotations(data["project_name"])
    return res


@blueprint.route("/status", methods=["GET"])
def string_ex_status():
    """Route to receive the status of the current job."""
    return "StringEx is installed and running..."


@blueprint.on(
    "send_to_cytoscape",
)
def string_send_to_cytoscape(message):
    """Send the selected nodes and links to Cytoscape."""
    return_dict = mp.Manager().dict()
    ip = flask.request.remote_addr
    user = message.get("user", util.generate_username())
    p = mp.Process(
        target=send_to_cytoscape,
        args=(message, ip, user, return_dict, GD.pfile, GD.sessionData["actPro"]),
    )
    p.start()
    p.join(timeout=300)
    p.terminate()
    if p.exitcode is None:
        return_dict["status"] = {
            "message": f"Process timed out. Please do not remove networks or views fom Cytoscape while the process is running.",
            "status": "error",
        }
    blueprint.emit("status", return_dict["status"])


@blueprint.on("reset_selection")
def string_ex_reset_selection():
    GD.sessionData["selected"] = []
    print("Selection reset.")
    blueprint.emit(
        "reset",
        {
            "message": f"Selection reset.",
            "status": "success",
        },
    )
