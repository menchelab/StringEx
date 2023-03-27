$(document).ready(function () {
  document.getElementById("string_spring").style.display = "block";
  document.getElementById("string_new_namespace_name").readOnly = true;
  $(function () {
    $("#string_upload_namespaces").selectmenu({
      classes: {
        "ui-selectmenu-open": "twozerozero-open",
      },
    });
  });
  $("#string_upload_namespaces").on("selectmenuselect", function () {
    var name = $("#string_upload_namespaces").find(":selected").text();
    console.log(name);
    //UpdateNamespace(name);
  });
  $(function () {
    $("#string_algo").selectmenu();
  });

  $("#string_algo").on("selectmenuselect", function () {
    var name = $("#string_algo").find(":selected").text();
    console.log("22: name: " + name);
    if (name.includes("tsne")) {
      document.getElementById("string_cg_tsne").style.display = "block";
      document.getElementById("string_cg_umap").style.display = "none";
      document.getElementById("string_spring").style.display = "none";
      document.getElementById("string_kamada_kawai").style.display = "none";
    } else if (name.includes("umap")) {
      document.getElementById("string_cg_umap").style.display = "block";
      document.getElementById("string_cg_tsne").style.display = "none";
      document.getElementById("string_spring").style.display = "none";
      document.getElementById("string_kamada_kawai").style.display = "none";
    } else if (name == "spring") {
      document.getElementById("string_cg_umap").style.display = "none";
      document.getElementById("string_cg_tsne").style.display = "none";
      document.getElementById("string_spring").style.display = "block";
      document.getElementById("string_kamada_kawai").style.display = "none";
    } else if (name == "kamada_kawai") {
      document.getElementById("string_cg_umap").style.display = "none";
      document.getElementById("string_cg_tsne").style.display = "none";
      document.getElementById("string_spring").style.display = "none";
      document.getElementById("string_kamada_kawai").style.display = "block"; // might be confusing when you cannot directly select the columns for weights
    } else {
      document.getElementById("string_cg_umap").style.display = "none";
      document.getElementById("string_cg_tsne").style.display = "none";
      document.getElementById("string_spring").style.display = "none";
      document.getElementById("string_kamada_kawai").style.display = "none";
    }
  });

  $(function () {
    const checkbox = document.getElementById("string_calc_lay");

    checkbox.addEventListener("change", (event) => {
      console.log("checkbox changed");
      if (event.currentTarget.checked) {
        $("#string_algo").selectmenu("enable");
      } else {
        $("#string_algo").selectmenu("disable");
      }
    });
  });

  $("#string_upload_button").button();
  $("input:radio[name='string_namespace']").change(function () {
    if ($(this).val() == "New") {
      document.getElementById("string_new_namespace_name").readOnly = false;
      $("#string_upload_namespaces").selectmenu("disable");
    } else {
      document.getElementById("string_new_namespace_name").readOnly = true;
      $("#string_upload_namespaces").selectmenu("enable");
    }
    console.log("37: New namespace:" + $("#new_namespace_name").val());
  });
  $("#string_new_namespace_name").on("click", function () {
    this.readOnly = false;
    $("#string_upload_namespaces").selectmenu("disable");
    document.getElementById("string_radio_new_namespace").checked = true;
  });
  $("#string_framebox_exisiting").on("click", function () {
    $("#string_new_namespace_name").readOnly = true;
    $("#string_upload_namespaces").selectmenu("enable");
    document.getElementById("string_radio_existing").checked = true;
  });
  $("#string_upload_form").on("change input", function () {
    console.log("changed!");
    var string_formData = new FormData(
      document.getElementById("string_upload_form")
    );
    for (var pair of string_formData.entries()) {
      console.log("47: pairs: " + pair[0] + ", " + pair[1]);
    }
  });

  $("#string_upload_form").submit(function (event) {
    console.log("Submitting");

    // document.getElementById("upload_button").style.backgroundImage = "{{ url_for('static', filename = 'img/active_gears.png') }}";
    $("#string_upload_message").html("");
    document.getElementById("string_upload_button").value = "...";
    document.getElementById("string_upload_button").disabled = true;
    document.getElementById("string_upload_processing").style.display = "block";

    event.preventDefault();

    var form = $(this);
    var formData = new FormData(this);
    if (formData.get("string_namespace") == "existing") {
      formData.append(
        "existing_namespace",
        $("#string_upload_namespaces").val()
      );
    }
    let it = formData.keys();

    let result = it.next();
    while (!result.done) {
      console.log("101: Result: " + result); // 1 3 5 7 9
      console.log("102: Result_value:" + formData.get(result.value));
      result = it.next();
    }
    console.log("107: dbprefix:", dbprefix);
    var base_url = "http://" + window.location.href.split("/")[2]; // Not sure why no todo it like this. Maybe if the server runs on a different ip than the uploader?
    var url = base_url + "/StringEx/uploadfiles";
    console.log(window.location.href);
    console.log("107: URL:", url);
    console.log("108: FormData:", formData);
    $.ajax({
      type: "POST",
      url: url,
      data: formData, // serializes the form's elements.
      cache: false,
      contentType: false,
      processData: false,
      success: function (data) {
        console.log("117: Data: " + data);
        $("#string_upload_message").html(data);
        document.getElementById("string_upload_button").value = "Upload";
        document.getElementById("string_upload_button").disabled = false;
        document.getElementById("string_upload_processing").style.display =
          "none";
      },
      error: function (err) {
        console.log("Uploaded failed!");
        $("#string_upload_message").html("Upload failed");
        document.getElementById("string_upload_button").value = "Upload";
        document.getElementById("string_upload_button").disabled = false;
        document.getElementById("string_upload_processing").style.display =
          "none";
      },
    });
  });
});
