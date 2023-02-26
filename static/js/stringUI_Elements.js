function selectEvidenceWebGL(id, layout) {
  if (!pdata["linksRGB"].includes(layout + "RGB")) {
    var button = document.getElementById(id);
    button.style.display = "none";
  }
  $("#" + id).on("click", function () {
    var links = document.getElementById("linksRGB");
    console.log(pdata);
    for (let i = 0; i < links.length; i++) {
      if (String(links[i].text).includes(layout)) {
        console.log("selected layout:" + links[i].text);
        document.getElementById("linksRGB").selectedIndex = i;
        console.log("index:" + $("#linksRGB option:selected").index());
        var url = new URL(window.location.href);
        url.searchParams.set("lcol", $("#linksRGB option:selected").index());
        url.searchParams.set("layout", $("#layouts option:selected").index());
        url.searchParams.set("ncol", $("#layoutsRGB option:selected").index());
        url.searchParams.set("project", pdata["name"]);
        window.location.href = url;
        break;
      }
    }
  });
}
function selectEvidenceVRNetzer(id, layout) {
  if (!pdata["linksRGB"].includes(layout + "RGB")) {
    var button = document.getElementById(id);
    button.style.display = "none";
  }

  $("#" + id).on("click", function () {
    var links = document.getElementById("links");
    console.log(layout);
    for (let i = 0; i < links.length; i++) {
      if (String(links[i].text).includes(layout)) {
        console.log("selected layout:" + links[i].text);
        link_xyz = links[i].text;
        break;
      }
    }
    var link_rgb = link_xyz.slice(0, -3) + "RGB";
    socket.emit("ex", { id: "linkcolors", opt: link_rgb, fn: "sel" });
    socket.emit("ex", { id: "links", opt: link_xyz, fn: "sel" });
  });
}
// function layoutDropdown (id, data, active){
//     console.log(id,data,active)
//     $('#'+ id).selectmenu();

//     for (let i = 0; i < data.length; i++) {
//       $('#'+ id).append(new Option(data[i]));
//     }
//     $('#'+ id).val(active);
//     $('#'+ id).selectmenu("refresh");

//     $('#'+ id).on('selectmenuselect', function () {
//       var name =  $('#'+ id).find(':selected').text();
//       socket.emit('ex', {id: id, opt: name, fn: "sel"});
//       ///logger($('#selectMode').val());
//     });

//   }

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
