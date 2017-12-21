function buildCard(color, card_title, card_body, card_action){
  return  "<div class='col s4 m3'>" +
          "<div class='card small " + color + " darken-1'>" +
           "<div class='card-content white-text'>" +
             "<span class='card-title'>" + card_title + "</span>" +
           "<p>" + card_body + "</p>" +
           "<div class='card-action'>" +
             "<a onClick='" + card_action + "' >Select</a>" +
           "</div>" +
         "</div>" +
         "</div>"
};

function getCourses(){
  $.get("/getCourses", function(courses, status){
    for (course in courses){
      var c = courses[course];
      $("#courseSelection").append(
	buildCard('blue-grey',
	  c['course_code'],
	  c['name'],
	  "getAssignments(" + c['id'] + ");"
	)
      );
    }
  });
};

function getAssignments(id){
  // Clear previous assignment entries
  $("#assignmentSelection").empty();

  $.get("/getAssignments?id=" + id, function(assignments, status){
    for (assignment in assignments){
      var a = assignments[assignment];
     $("#assignmentSelection").append(
        buildCard('green',
	  a['name'],
	  a['description'],
	  "getSubmissions(" + a['course_id'] + "," + a['id'] + ");"
	)
     ); 
    }
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

  $.get("/getSubmissions?course_id=" + course_id +"&assignment_id=" + assignment_id, function(submissions, status){
    $("#submissionsDisplay").append(
     "<div class='card-panel teal'>" +
       "<p class='white-text'>Number of submissions received: " + submissions.length + "</p>" +
       "<a class='btn halfway waves-effect waves-light red'>Submit to Moss</a>" +
     "</div>" 
    );
  });

  // Scroll down if there is a long list of courses and assignments
  setTimeout( function(){
    $("html, body").animate({
      scrollTop: $("#submissionsDisplay").offset().top
    }, 2000);
  }, 500);
};

$(document).ready(function() {
  getCourses();
});
