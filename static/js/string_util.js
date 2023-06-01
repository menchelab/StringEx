function makeid(length) {
  let result = "";
  const characters =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  const charactersLength = characters.length;
  let counter = 0;
  while (counter < length) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
    counter += 1;
  }
  return result;
}
function initSelectmenu(event, id) {
  stringExSocket.emit(event, {
    usr: uid,
  });
  stringExSocket.on(event, function (message) {
    if (message.usr == uid) {
      $.each(message.data, function (i, item) {
        $("#" + id).append(
          $("<option>", {
            value: item,
            text: item,
          })
        );
      });
      $("#" + id).selectmenu("refresh");
    }
  });
}
$(document).ready(function () {
  $("input[type='button']").tooltip({
    show: { duration: "fast" },
    hide: { duration: "fast" },
    position: {
      my: "left bottom+31",
      at: "left bottom",
      collision: "flipfit",
    },
  });
});
