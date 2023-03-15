$(document).ready(function () {
  ///set up and connect to socket
  console.log("http://" + window.location.host + "/chat");
  socket = io.connect("http://"+ window.location.host  + "/chat");
  socket.io.opts.transports = ["websocket"];
  socket.on("connect", function () {
    socket.emit("join", { uid: uid });
  });
  socket.on("disconnect", function () {
    console.log("disconnected - trying to connect");
    location.reload();
  });
});
