function buildCard(color, card_title, card_body, card_action){
  return  "<div class='col s4 m3'>" +
          "<div class='card small " + color + " darken-1'>" +
           "<div class='card-content white-text'>" +
             "<span class='card-title'>" + card_title + "</span>" +
           "<p>" + card_body + "</p>" +
           "<div class='card-action " + color + "'>" +
             "<a onClick='" + card_action + "' >Select</a>" +
           "</div>" +
         "</div>" +
         "</div>"
};

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
      courses = data.responseJSON['course_list'];
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

      if (data.responseJSON['links'] !== undefined){
        var links = data.responseJSON['links'];
        $("#courseSelection").after(
          "<div class='row' id='nav_btns_row'><div class='col s12' id='nav_btns_col'>"
        );
        for (link in links){
          $("#nav_btns_col").append(
            "<a class='btn' onclick='getCourses(\"" + links[link] + "\");'>" + link + "</a>"
          );
        }
	$("#nav_btns_row").after(
          "</div></div>"
        );
      }
    }
  });
};

function getAssignments(id){
  // Clear previous assignment entries
  $("#assignmentSelection").empty();
  $("#submissionsDisplay").empty();

  $.get("/getAssignments?id=" + id, function(assignments, status){
    for (assignment in assignments){
      var a = assignments[assignment];
      var description = a['description'];

      if (description === null){
        description = "No description";
      } else {
        description = description.replace(/<{1}[^<>]{1,}>{1}/g," ");
      }

      $("#assignmentSelection").append(
         buildCard('green',
 	  a['name'],
	  description,
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

  $.get("/getSubmissions?course_id=" + course_id + "&assignment_id=" + assignment_id, function(submissions, status){
    $("#submissionsDisplay").append(
     "<div class='card-panel teal'>" +
       "<p class='white-text'>Number of submissions received: " + submissions.length + "</p>" +
       "<label class='white-text'>Input your Moss User ID: <input id='moss_id' type='text-input' class='black-text'></label><br /><br />" +
       "<a class='btn halfway waves-effect waves-light red' id='moss_submit_btn' " +
         "onclick='submitToMoss(" + course_id + "," + assignment_id +");'>" +
         "Submit to Moss</a>" +
       "<div id='moss_response'></div>" +
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

function submitToMoss(course_id, assignment_id){
  $("#moss_submit_btn").prop("disabled", true);
  $("#moss_response").empty();
  $("#moss_response").append("<div class='progress'><div class='indeterminate'></div></div>");

  $.get("/submitToMoss?course_id=" + course_id + "&assignment_id=" + assignment_id + "&moss_id=" + $("#moss_id").val(),
    function(url, status){
      $("#moss_response").empty();
      $("#moss_response").append("<span class='white-text'>See the Moss report at: " +
        "<a class='indigo-text' href='" + url + "'>" + url + "</a></span>");
    }
  );
};

$(document).ready(function() {
  $("#courseSelection").append(
    '<div <div class="preloader-wrapper big active"><div class="spinner-layer spinner-blue"><div class="circle-clipper left"><div class="circle"></div></div><div class="gap-patch"><div class="circle"></div></div><div class="circle-clipper right"><div class="circle"></div></div></div>'
  );
  getCourses();
});
