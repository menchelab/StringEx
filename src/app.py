import json
import os

import flask
import GlobalData as GD
from flask_socketio import emit
from PIL import Image

import uploader

from . import settings as st
from . import util as string_util
from . import workflows as wf
from . import routes
import util

url_prefix = "/StringEx"

blueprint = flask.Blueprint(
    "StringEx",
    __name__,
    url_prefix=url_prefix,
    template_folder=st._THIS_EXT_TEMPLATE_PATH,
    static_folder=st._THIS_EXT_STATIC_PATH,
)

main_tabs = ["string_main_tab.html"]
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
    out = wf.VRNetzer_send_network_workflow(receiveNetwork)
    project = receiveNetwork["form"]["project"]
    return json.dumps({"url": f"/StringEx/resultPage/{project}/{','.join(out)}"})


@blueprint.route("/resultPage/<project>/<layouts>", methods=["GET"])
def string_ex_result_page(project, layouts=None):
    """Route to the results page project depended."""
    username = util.generate_username()
    layouts = layouts.split(",")
    flask.session["username"] = username
    flask.session["room"] = 1
    return flask.render_template(
        "string_send_result_page.html",
        project=project,
        layouts=layouts,
        pfile=json.dumps(GD.pfile),
        sessionData=json.dumps(GD.sessionData),
    )
