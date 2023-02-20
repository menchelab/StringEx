$(document).ready(function () {
  stringExSocket = io.connect(
    "http://" + location.hostname + ":" + location.port + "/StringEx"
  );
  stringExSocket.on("status", function (data) {
    console.log(data["message"]);
    button = document.getElementById("stringex_send_network_to_cy_button");
    button.value = "Send";
    button.disabled = false;
    if (data["status"] == "error") {
      $("#stringex_SM").css("color", "red");
    } else {
      $("#stringex_SM").css("color", "green");
    }
    $("#stringex_send_network_to_cy_button").removeClass("loadingButton");
    $("#stringex_SM").text(data["message"]);
    $("#stringex_SM").css("opacity", "1");
    setTimeout(function () {
      $("#stringex_SM").css("opacity", "0");
    }, 5000);
  });

  var ip = document.getElementById("stringex_client_ip").getAttribute("value");
  console.log("IP is:", ip);

  initButton("stringex_send_network_to_cy_button");
  $("#stringex_send_network_to_cy_button").on("click", function () {
    button = document.getElementById("stringex_send_network_to_cy_button");
    button.value = "";
    button.disabled = true;
    $("#stringex_send_network_to_cy_button").addClass("loadingButton");
    if ($("#stringex_to_host").is(":checked")) {
      ip = "localhost";
    }
    message = {
      ip: ip,
      username: username,
      layout: $("#stringex_send_layout_select").val(),
      color: $("#stringex_send_color_select").val(),
    };
    console.log(message);
    stringExSocket.emit("send_to_cytoscape", message);
  });
  // $("#stringex_reset_selection").on("click", function () {
  //   sessionData["selected"] = [];
  //   stringExSocket.emit("reset_selection");
  //   document.getElementById("stirngex_num_nodes").innerHTML =
  //     sessionData["selected"].length;
  //   console.log("reset selection");
  // });
  // stringExSocket.on("reset", function (message) {
  //   sessionData["selected"] = [];
  //   document.getElementById("stirngex_num_nodes").innerHTML =
  //     sessionData["selected"].length;
  //   console.log("reset selection");
  // });
});
