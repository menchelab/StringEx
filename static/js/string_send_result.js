var socket;
var lastval = 0;
/// UE4 connection

/// ue4 to webui routes

ue.interface.nodelabels = function (data) {
  console.log(data);
  var text = '{"id":"x", "data": [1,2,4], "fn": "x"}';
  var out = JSON.parse(text);
  out.id = "nl";
  out.data = data;
  socket.emit("ex", out);
};

ue.interface.nodelabelclicked = function (data) {
  console.log(data);
  var text = '{"id":"x", "data": -1, "fn": "nlc"}';
  var out = JSON.parse(text);
  out.data = data;
  socket.emit("ex", out);
};

function settextscroll(id, val) {
  var box = document.getElementById(id).shadowRoot.getElementById("box");
  $(box).scrollTop(val[0]);
  $(box).scrollLeft(val[1]);
}

$(document).ready(function () {
  ///set up and connect to socket
  console.log(window.location.host + ":" + "/chat");
  socket = io.connect(window.location.host + ":" + "/chat");
  socket.io.opts.transports = ["websocket"];

  socket.on("connect", function () {
    socket.emit("join", { uid: uid });
  });
});
