$(document).ready(function () {
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
});
