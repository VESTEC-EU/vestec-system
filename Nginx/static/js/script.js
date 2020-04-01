var all_activities = {};
var user_type=-1;

function checkAuth() {
    // need to add a check to flask to see if the token in the session is the same as the current user's
    var jwt_token = sessionStorage.getItem("access_token");

    if (typeof jwt_token === 'undefined' || jwt_token === null || jwt_token === '') {
        window.location.href = "/login";
    } else {
        $.ajax({
            url: "/flask/authorised",
            type: "GET",
            headers: {'Authorization': 'Bearer ' + jwt_token},
            success: function(response) {
                if (response.status == 200) {                    
                    $("#body").load("../templates/loggedin.html");
                    generateNavigationBar();
                } else {
                    window.location.href = "/login";
                }
            },
            error: function(xhr) {
                window.location.href = "/login";
            }
        });
    }
}

$("#checkJobStatus").hide();

$(function() {
    //$("#body-container").load("../templates/createJobWizard.html");
    getJobsDashboard();
});

$("#userInput").keyup(function(e) {
    if (e.keyCode == 13) {
        submitJob();
    }
});

$("#signup").click(function() {
    window.location.replace("/signup");
});

function userLogin() {
    var user = {};
    user["username"] = $("#username").val();
    user["password"] = $("#password").val();

    if (user["username"] == '' && user["password"] == '') {
        $("#login-message").html("Please enter a username and password.");
        $("#login-message").show();
    } else {
        $.ajax({
            url: "/flask/login",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(user),
            dataType: "json",
            success: function(response) {
                if (typeof response.access_token !== 'undefined' && response.access_token !== '') {
                    sessionStorage.setItem("access_token", response.access_token);
                    window.location.href = "/home";
                } else {
                    $("#login-message").html(response.msg);
                    $("#login-message").show();
                }
            },
            error: function(xhr) {
                $("#login-message").html("Sorry, there seems to be a problem with our system");
                $("#login-message").removeClass().addClass("button white-btn red-high-btn self-left");
                $("#login-message").show();
            }
        });
    }
}

function getJobWizard() {
    $("#nav-home").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#nav-dash").addClass("blue");
    $("#body-container").load("../templates/createJobWizard.html");
    $.ajax({
        url: "/flask/getmyworkflows",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {            
            var workflows = JSON.parse(response);
            $("#incidentType").empty();
            for (item in workflows) {
                item = workflows[item];                                                   
                $("#incidentType").append("<option value='"+item+"'>"+item+"</option>");                
            }            
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User workflow lookup failed");
        }
    });
}

function submitJob() {
    var job = {}
    job["incidentType"] = $("#incidentType").val();
    job["incidentName"] = $("#incidentName").val();
    
    $.ajax({
        url: "/flask/createincident",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(job),
        dataType: "json",
        success: function(response) {
            if (response.status == "201") {
                $("#userInput").val('');
                $("#confirmation").html("<span>&#10003</span>" + response.msg);
                $("#confirmation").removeClass().addClass("button white-btn green-high-btn self-center");
                $("#confirmation").show();
            } else {
                $("#confirmation").html("<span>&#10007</span>" + response.msg);
                $("#confirmation").removeClass().addClass("button white-btn amber-high-btn self-center");
                $("#confirmation").show();
            }
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error creating new incident");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function generateNavigationBar() {
  var html_code="<div id=\"nav-home\" class=\"blue menu_item\" onClick=\"getJobsDashboard()\">Home</div>\<div id=\"nav-dash\" class=\"menu_item\" onClick=\"getJobWizard()\">New incident</div>"
  html_code+="<div id=\"nav-logout\" class=\"self-right menu_item\" onClick=\"logOut()\">Log Out</div>"
  // We store the user type to avoid hitting the server, as the activities are also protected on the server then at worst a user could
  // force the menu to display but couldn't action any of the activities under it
  if (user_type == -1) {
    $.ajax({
      url: "/flask/user_type",
      type: "GET",
      headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
      success: function(response) {
        if (response.status == 200) {
          user_type = JSON.parse(response.access_level);
          generateNavigationBar();
        } else {
          console.log({"status": 400, "msg": "Sorry, there seems to be a problem with the look up of user authorisation level"});
        }
      },
      error: function(xhr) {
        console.log({"status": 500, "msg": "Sorry, there seems to be a problem with our system."});
      }
    });
    user_type
  } else if (user_type > 0) {
    html_code+=generateAdminDropdown();
  }
  $("#navigation_bar").html(html_code);
}

function generateAdminDropdown() {
  var admin_html="<div class=\"admin_dropdown\">";
  admin_html+="<button class=\"dropbtn\">Admin<i class=\"fa fa-caret-down\"></i></button>";
  admin_html+="<div class=\"admin_dropdown_content\">";
  admin_html+="<div class=\"admin_item\" onClick=\"getLogs()\">Logs</div>";
  admin_html+="<div class=\"admin_item\" onClick=\"getSystemHealth()\">System health</div>";
  admin_html+="<div class=\"admin_item\" onClick=\"getWorkflows()\">Workflows</div>";
  admin_html+="<div class=\"admin_item\" onClick=\"getUsers()\">Users</div>";
  admin_html+="</div></div>";
  return admin_html;
}

function getJobsDashboard() {
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#nav-home").addClass("blue");
    $("#body-container").html("");

    $.ajax({
        url: "/flask/getincidents",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            if (response.status == 200) {
                all_incidents = JSON.parse(response.incidents);
                loadIncidentCards(all_incidents);
            } else {
                console.log({"status": 400, "msg": "Sorry, there seems to be a problem with the extraction of activities."});
            }
        },
        error: function(xhr) {
            console.log({"status": 500, "msg": "Sorry, there seems to be a problem with our system."});
        }
    });
}

function loadIncidentCards(incidents) {
    // order = string; if "ASC", the list of jobs is loaded in ascending order, if "DESC", in descending order
    $.get("../templates/jobCard.html", function(template) {
        $('<div id="dashboard" class="w3-container">').appendTo("#body-container");

        for (incident in incidents) {
            createIncidentCard(template, incidents[incident]);
        }

        $('</div>').appendTo("#body-container");
    });
}

function createIncidentCard(template, incident) {    
    var card = $(template)[0];
    //$(card).attr("id", "card_" + index);
    $(card).find("#cardTitle").html(incident.name);
    
    $(card).find("#cardBody").html("<p><b>Kind: </b>" + incident.kind + "</p><p><b>Incident on: </b>" + incident.incident_date + "</p><p><b>Created by: </b>" + incident.creator+"</p>");
    $(card).find("#cardStatus").html(incident.status);
    $(card).find("#viewDetails").attr('onClick', "getIncidentDetails(\"" + incident.uuid + "\")");
    $(card).find("#cardTitle").attr('onClick', "getIncidentDetails(\"" + incident.uuid + "\")");
    $("#dashboard").append(card);
}

function getIncidentDetails(incident_uuid) {
    $("#nav-home").removeClass("blue");    

    $.ajax({
        url: "/flask/incident/" + incident_uuid,
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            incident_details = JSON.parse(response.incident);            
            $("#body-container").html(loadIncidentDetails(incident_details));            
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Incident detail retrieval failed");
        }
    });
}

function loadIncidentDetails(incident) {
    var job_html = '<div class="jobDetails self-center">';
    job_html += '<div class="jobLine"><b>UUID: </b><div>' + incident.uuid + '</div></div>';
    job_html += '<div class="jobLine"><b>Name: </b><div>' + incident.name + '</div></div>';
    job_html += '<div class="jobLine"><b>Kind: </b><div>' + incident.kind + '</div></div>';
    job_html += '<div class="jobLine"><b>Created On: </b><div>' + incident.incident_date + '</div></div>';
    job_html += '<div class="jobLine"><b>Created By: </b><div>' + incident.creator + '</div></div>';
    job_html += '<div class="jobLine"><b>Status: </b><div>' + incident.status + '</div></div>';

    /*
    if (job.status == "QUEUED") {
        job_html += '<div class="jobLine"><b>Status: </b><button id="jobStatus" class="button amber self-right">' + job.status + '</button></div>';
    } else if (job.status == "RUNNING") {
        job_html += '<div class="jobLine"><b>Status: </b><button id="jobStatus" class="button green self-right">' + job.status + '</button></div>';
    } else if (job.status == "ERROR") {
        job_html += '<div class="jobLine"><b>Status: </b><button id="jobStatus" class="button red self-right">' + job.status + '</button></div>';
    } else {
        job_html += '<div class="jobLine"><b>Status: </b><button id="jobStatus" class="button blue self-right">' + job.status + '</button></div>';
    }
    */

    job_html += '</div>';

    return job_html;
}

function createWorkflow() {
    var wf = {};
    wf["kind"] = $("#workflowname").val();
    wf["queuename"] = $("#workflowqueuename").val();
    $.ajax({
        url: "/flask/addworkflow",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            getWorkflows();
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error adding workflow");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function deleteWorkflow(kind) {
    var wf = {};
    wf["kind"] = kind;
    $.ajax({
        url: "/flask/deleteworkflow",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            getWorkflows();
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error removing workflow");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function getWorkflows() {
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/workflows.html");

    $.ajax({
        url: "/flask/workflowinfo",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            var workflows = JSON.parse(response);
            $("#workflowTable").append("<tbody>");

            for (item in workflows) {
                var wf_entry = "<tr>";
                item = workflows[item];
                wf_entry += "<td>" + item.kind + "</td>";
                wf_entry += "<td>" + item.queuename + "</td>";
                wf_entry += "<td><img src='../img/cross.png' width=32 height=32 onClick=\"deleteWorkflow('"+item.kind+"')\"></td>";
                
                wf_entry += "</tr>";

                $("#workflowTable").append(wf_entry);
            }
            $("#workflowTable").append("</tbody>");
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Workflow retrieval failed");
        }
    });
}

function getUsers() {
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/users.html");   

    $.ajax({
        url: "/flask/getallusers",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            var users = JSON.parse(response);
            $("#userTable").append("<tbody>");

            for (item in users) {
                var user_entry = "<tr>";
                item = users[item];
                user_entry += "<td><span class=\"link\" onclick=\"manageUser('"+item.username+"');\">" + item.username + "</span></td>";
                user_entry += "<td>" + item.name + "</td>";
                user_entry += "<td>" + item.email + "</td>";
                if (item.access_rights == 0) {
                    user_entry += "<td>user</td>";
                } else if (item.access_rights == 1) {
                    user_entry += "<td>administrator</td>";
                }
                
                user_entry += "<td></td>";
                
                user_entry += "</tr>";

                $("#userTable").append(user_entry);
            }
            $("#userTable").append("</tbody>");
            $("#userDetails").hide();
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User retrieval failed");
        }
    });
}

function addWorkflowToUser() {
    var data = {};
    var username=$('#usernameh2').text();
    data["username"] = username;
    data["workflow"] = $('#all_registeredworkflows').val();
    $.ajax({
        url: "/flask/addusertoworkflow",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(data),
        dataType: "json",
        success: function(response) {
            manageUser(username);
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User edit failed");
        }
    });
}

function removeWorkflowFromUser() {
    var data = {};
    var username=$('#usernameh2').text();
    data["username"] = username;
    data["workflow"] = $('#registeredworkflows_users').val();
    $.ajax({
        url: "/flask/removeuserfromworkflow",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(data),
        dataType: "json",
        success: function(response) {
            manageUser(username);
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User edit failed");
        }
    });
}

function manageUser(username) {
    var wf = {};
    wf["username"] = username;
    var workflows;
    var users;
    $.when(
    $.ajax({
        url: "/flask/workflowinfo",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            workflows = JSON.parse(response);
        }
    }),
    $.ajax({
        url: "/flask/getuser",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            users = JSON.parse(JSON.stringify(response));            
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User retrieval failed");
        }
    })
    ).then(function() {
        user=users[0]
        $('#usernameh2').text(user.username);
        $('#name').val(user.name)
        $('#email').val(user.email)
        if (user.access_rights == 0) {
            $('#type').val("user");
        } else if (user.access_rights == 1) {
            $('#type').val("administrator");
        }
        $('#enabled').prop('checked', user.enabled);
        $("#registeredworkflows_users").empty();
        for (wf in user.workflows) {
            wf=user.workflows[wf];
            $("#registeredworkflows_users").append($('<option>', {value:wf, text: wf}))
        }
        $("#all_registeredworkflows").empty();
        for (wf in workflows) {
            wf=workflows[wf].kind;
            $("#all_registeredworkflows").append("<option value='"+wf+"'>"+wf+"</option>");
        }
        $("#userTable").hide();
        $("#userDetails").show();
    });
}

function editUser() {
    var wf = {};
    wf["username"] = $("#usernameh2").text();
    wf["name"] = $("#name").val();
    wf["email"] = $("#email").val();
    wf["type"] = $("#type").val();
    wf["enabled"] = $("#enabled").prop('checked');
    $.ajax({
        url: "/flask/edituser",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            getUsers();
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User edit failed");
        }
    });
}

function getSystemHealth() {
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/health.html");
    $.ajax({
        url: "/flask/health",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            var health = JSON.parse(response);
            $("#healthTable").append("<tbody>");

            for (item in health) {
                var health_entry = "<tr>";
                item = health[item];
                health_entry += "<td>" + item.name + "</td>";
                if (item.status == true) {
                    health_entry += "<td><img src='../img/tick.png' width=32 height=32></td>";
                } else {
                    health_entry += "<td><img src='../img/cross.png' width=32 height=32></td>";
                }
                health_entry += "</tr>";

                $("#healthTable").append(health_entry);
            }
            $("#healthTable").append("</tbody>");
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Health check failed");
        }
    });
}

function getLogs() {
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/logs.html");

    $.ajax({
        url: "/flask/logs",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            var logs = JSON.parse(response);
            $("#logsTable").append("<tbody>");

            for (log in logs) {
                var log_entry = "<tr>";
                log = logs[log];
                log_entry += "<td>" + log.timestamp + "</td>";
                log_entry += "<td>" + log.originator + "</td>";
                log_entry += "<td>" + log.user + "</td>";
                log_entry += "<td>" + log.type + "</td>";
                log_entry += "<td>" + log.comment + "</td>";
                log_entry += "</tr>";

                $("#logsTable").append(log_entry);
            }
            $("#logsTable").append("</tbody>");
            document.querySelector("#tableSearch").addEventListener('keyup', searchTable, false);
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Logs check failed");
        }
    });
}

function searchTable(event) {
    var search = event.target.value.toUpperCase();
    var rows = document.querySelector("#logsTable tbody").rows;

    for (var i = 0; i < rows.length; i++) {
        var origin_col = rows[i].cells[1].textContent.toUpperCase();
        var type_col = rows[i].cells[3].textContent.toUpperCase();
        var comment_col = rows[i].cells[4].textContent.toUpperCase();

        if (origin_col.indexOf(search) > -1 || type_col.indexOf(search) > -1 || comment_col.indexOf(search) > -1) {
            rows[i].style.display = "";
        } else {
            rows[i].style.display = "none";
        }
    }
}

function logOut() {
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").addClass("blue");

    $.ajax({
        url: "/flask/logout",
        type: "DELETE",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            if (response.status == 200) {
                sessionStorage.removeItem("access_token");
                window.location.href = "/login";
            }
        }
    });
}

