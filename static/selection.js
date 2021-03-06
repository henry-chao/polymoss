function getCourses(url){
  $.ajax({
    url: "/getCourses",
    dataType: 'json',
    contentType: 'application/json',
    data: JSON.stringify('{"url":"' + url + '"}'),
    type: 'POST',
    complete: function(data, status){
      $("#courseSelection").empty();
      $("#nav_btns_row").remove();
      $("#courseSelection").append( data.responseText );
    }
  });
};

function getAssignments(id){
  // Clear previous assignment entries
  $("#assignmentSelection").empty();
  $("#assignmentSelection").append("<div class='progress'><div class='indeterminate'></div></div>");

  $.get("/getAssignments?id=" + id, function(data, status){
    $("#assignmentSelection").empty();
    $("#assignmentSelection").append( data );
  });

  // Scroll down if there is a long list of courses and assignments
  setTimeout( function(){
    $("html, body").animate({
      scrollTop: $("#assignmentSelection").offset().top
    }, 2000);
  }, 500);
};

var submission_assignments = {}
function addAssignmentToSubmissions(course_id, assignment_id, assignment_name){
  if(submission_assignments[assignment_name] == null){
    $("#submission_assignments").append("<div class='chip assignment_chip'>" + assignment_name + "<i class='close material-icons'>close</i></div>");
    submission_assignments[assignment_name] = {"course_id": course_id, "assignment_id": assignment_id};
    $('.assignment_chip').click(function() {
      assignment_name = $( this ).text();
      assignment_name = assignment_name.substring(0, assignment_name.length - 5);
      delete submission_assignments[assignment_name];
      if (Object.keys(submission_assignments).length == 0) {
        $("#moss_submit_btn").addClass('disabled');
      };
      $( this ).remove();
    });

    $("#moss_submit_btn").removeClass('disabled');
  };
};

function submitToMoss(){
  $("#moss_submit_btn").addClass("disabled");
  $("#moss_response").empty();
  $("#moss_response").append("<div class='progress'><div class='indeterminate'></div></div>");

  var base_file_location = null;
  if( $("#base_file")[0].files.length > 0) {
    var form_data = new FormData($("#base_submission")[0]);
    $.ajax({
      type: 'post',
      url: '/uploadBaseFile',
      data: form_data,
      processData: false,
      contentType: false
    }).done(function(data) {
        submission_data = {
          'code_type': $("#code_type").val(),
          'submissions': submission_assignments,
          'base_files': [data]
        }
        get_moss_report(submission_data);
    });
  } else {
    submission_data = {
      'code_type': $("#code_type").val(),
      'submissions': submission_assignments
    }
    get_moss_report(submission_data);
  }
};

function get_moss_report(data){
  $.ajax({
    type: 'post',
    url: '/submitToMoss',
    data: JSON.stringify(data),
    contentType: 'application/json'
  }).done( function(url, status) {
    $("#moss_response").empty();
    $("#moss_response").append("<span class='white-text'>See the Moss report at: " +
      "<a class='indigo-text' target='_blank' href='" + url + "'>" + url + "</a></span>");
    $("#moss_submit_btn").removeClass("disabled");
  }).fail( function(jqXHR, status, error) {
    $("#moss_response").empty();
    $("#moss_response").append("<span class='red-text text-darken-4'>An error has occured during the MOSS submission process</span>");
    $("#moss_submit_btn").removeClass("disabled");
  });
}

$(document).ready(function() {
  $('#code_type').material_select();
  getCourses();
});
