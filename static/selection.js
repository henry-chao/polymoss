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
  $("#submissionsDisplay").empty();

  $.get("/getAssignments?id=" + id, function(data, status){
    $("#assignmentSelection").append( data );
  });

  // Scroll down if there is a long list of courses and assignments
  setTimeout( function(){
    $("html, body").animate({
      scrollTop: $("#assignmentSelection").offset().top
    }, 2000);
  }, 500);
};

function getSubmissions(course_id, assignment_id){
  $("#submissionsDisplay").empty();

  $.get("/getSubmissions?course_id=" + course_id + "&assignment_id=" + assignment_id, function(data, status){
    $("#submissionsDisplay").append( data );
    $('#code_type').material_select();
  });

  // Scroll down if there is a long list of courses and assignments
  setTimeout( function(){
    $("html, body").animate({
      scrollTop: $("#submissionsDisplay").offset().top
    }, 2000);
  }, 500);
};

function submitToMoss(course_id, assignment_id){
  $("#moss_submit_btn").prop("disabled", true);
  $("#moss_response").empty();
  $("#moss_response").append("<div class='progress'><div class='indeterminate'></div></div>");

  $.get("/submitToMoss?course_id=" + course_id + "&assignment_id=" + assignment_id + "&code_type=" + $("#code_type").val(),
    function(url, status){
      $("#moss_response").empty();
      $("#moss_response").append("<span class='white-text'>See the Moss report at: " +
        "<a class='indigo-text' target='_blank' href='" + url + "'>" + url + "</a></span>");
    }
  ).fail(function(){
    $("#moss_response").empty();
    $("#moss_response").append("<span class='red-text text-darken-4'>An error has occured during the MOSS submission process</span>");
  });
};

$(document).ready(function() {
  getCourses();
});
