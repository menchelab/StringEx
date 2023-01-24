function selectEvidenceWebGL(id, opt) {
    $('#' + id).on("click", function() {
        var links = document.getElementById("linksRGB");
        console.log(pdata);
        for (let i = 0; i < links.length; i++) {
            if (String(links[i].text).includes(opt)) {
                console.log("selected layout:" + links[i].text);
                document.getElementById("linksRGB").selectedIndex = i;
                console.log("index:"+$('#linksRGB option:selected').index())
                var url = window.location.href.split('&')[0] + '&project=' + pdata["name"] + '&layout=' + $('#layouts option:selected').index() + '&ncol=' + $('#layoutsRGB option:selected').index() + '&lcol=' + $('#linksRGB option:selected').index();
                window.location.href = url;
                break;
            }
        }
    });
}
function selectEvidenceVRNetzer(id, layout) {
    $('#' + id).on("click", function() {
        var links = document.getElementById("links");
        console.log(layout)
        for (let i = 0; i < links.length; i++) {
            if (String(links[i].text).includes(layout)) {
                console.log("selected layout:" + links[i].text);
                link_xyz = links[i].text;
                break;
            }
        }
        var link_rgb = link_xyz.slice(0,-3) + "RGB";
        socket.emit('ex', { id: "linkcolors", opt: link_rgb, fn: "sel" });
        socket.emit('ex', { id: "links", opt: link_xyz, fn: "sel" });
    });
}
function stringForwardButton(id,data) {
    $('#' + id).on("click", function() {
        console.log(data)
        // socket.emit('ex', { id: "linkcolors", opt: opt, fn: "sel" });
    });
}
function layoutDropdown (id, data, active){
    console.log(id,data,active)
    $('#'+ id).selectmenu();
  
    for (let i = 0; i < data.length; i++) {
      $('#'+ id).append(new Option(data[i]));
    }
    $('#'+ id).val(active);
    $('#'+ id).selectmenu("refresh");
  
    $('#'+ id).on('selectmenuselect', function () {
      var name =  $('#'+ id).find(':selected').text();
      socket.emit('ex', {id: id, opt: name, fn: "sel"});
      ///logger($('#selectMode').val());
    });
  
  }

/**
 * Will turn off the change of Link layouts if network is a string network
 */
function deactiveLinkLayouts() {
    var code =`
    <div class="twelve columns" hidden="true">
        <div class="slideTwo">
            <input type="checkbox" value="false" id="chbLrgb" name="check" unchecked></checkbox>
            <script>
                initCheckbox("chbLrgb");
            </script>
        </div>
    </div>

    <div class="twelve columns" hidden="true">
        <div class="slideTwo">
            <input type="checkbox" value="false" id="chbLxyz" name="check" unchecked></checkbox>
            <script>
                initCheckbox("chbLxyz");
            </script>
        </div>
    </div>`;
    document.write(code)
}
/**
 * Will turn on the change of Link layouts if network isn't a string network
 */
function activateLinkLayouts() {
    var code =`
    <div class="twelve columns" hidden="true">
        <div class="slideTwo">
            <input type="checkbox" value="false" id="chbLrgb" name="check" checked></checkbox>
            <script>
                initCheckbox("chbLrgb");
            </script>
        </div>
    </div>

    <div class="twelve columns" hidden="true">
        <div class="slideTwo">
            <input type="checkbox" value="false" id="chbLxyz" name="check" checked></checkbox>
            <script>
                initCheckbox("chbLxyz");
            </script>
        </div>
    </div>`;
    document.write(code)
}