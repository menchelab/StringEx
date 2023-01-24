$(document).ready(function() { 
  $("#string_map_preview").hide();
  $(function() {
    $("#string_organism").selectmenu();
  });
  $("#string_map_button").button();
  $("#string_upload_button").button();
  $("#string_map_form").on("change input", function() {
    console.log("changed!");
    var formData = new FormData(document.getElementById("string_map_form"));
  });
  
  $("#string_map_form").submit(function(event) {
    $("#string_map_preview").hide();
    $("#string_map_message").html("");
    document.getElementById("string_map_button").value = '...';
    document.getElementById("string_map_button").disabled = true;
    document.getElementById("string_map_processing").style.display = "block";
  
    event.preventDefault();
  
    var form = $(this);
    var formData = new FormData(this);
    let it = formData.keys();
  
    let result = it.next();
    while (!result.done) {
      console.log("101: Result: " + result); // 1 3 5 7 9
      console.log("102: Result_value:" + formData.get(result.value));
      result = it.next();
    }
    var base_url = "http://" + window.location.href.split("/")[2]; // Not sure why no todo it like this. Maybe if the server runs on a different ip than the uploader?
    var url = base_url + "/StringEx/mapfiles";
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
        $("#string_map_message").html(data);
        document.getElementById("string_map_button").value = 'Map';
        document.getElementById("string_map_button").disabled = false;
        document.getElementById("string_map_processing").style.display = "none";
      },
      error: function (err) {
        console.log("Uploaded failed!");
        $("#string_map_message").html("Mapping failed");
        document.getElementById("string_map_button").value = 'Map';
        document.getElementById("string_map_button").disabled = false;
        document.getElementById("string_map_processing").style.display = "none";
      },
    });

  });
});
