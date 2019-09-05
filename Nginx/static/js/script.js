var all_activities = {};

function checkAuth() {
    // need to add a check to flask to see if the token in the session is the same as the current user's
    var jwt_token = sessionStorage.getItem("access_token");

    if (typeof jwt_token === 'undefined' || jwt_token === null || jwt_token === '') {
        window.location.href = "/login";
    }
}

$("#checkJobStatus").hide();

$(function() {
    $("#body-container").load("../templates/createJobWizard.html");
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
        $("#login-message").text("Please enter a username and password.");
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
                    $("#login-message").text("Username or password incorrect. Please try again.");
                    $("#login-message").show();
                }
            },
            error: function(xhr) {
                $("#login-message").text("Username or password incorrect. Please try again.");
                $("#login-message").show();
            }
        });
    }
}

function getJobWizard() {
    $("#nav-dash").removeClass("blue");
    $("#nav-logs").removeClass("blue");
    $("#nav-home").addClass("blue");
    $("#body-container").load("../templates/createJobWizard.html");
}

function submitJob() {
    var job = {}
    job["job_name"] = $("#userInput").val();

    if (job["job_name"] == "") {
        $("#confirmation").removeClass().addClass("button amber self-center");
        $("#confirmation").html("<span>&#9888</span> Please enter a job name");
        $("#confirmation").show();
    } else {
        $.ajax({
            url: "/flask/submit",
            type: "PUT",
            headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
            contentType: "application/json",
            data: JSON.stringify(job),
            dataType: "text",
            success: function(response) {
                if (response == "True") {
                    $("#userInput").val('');
                    $("#confirmation").show();
                    $("#confirmation").removeClass().addClass("button green self-center");
                    $("#confirmation").html("<span>&#10003</span> Job successfully submitted");
                } else {
                    $("#confirmation").show();
                    $("#confirmation").removeClass().addClass("button red self-center");
                    $("#confirmation").html("<span>&#10007</span> Job submission failed");
                }
            },
            error: function(xhr) {
                $("#confirmation").show();
                $("#confirmation").removeClass().addClass("button red self-center");
                $("#confirmation").html("<span>&#10007</span> Job submission failed");
            }
        });
    }
}

function getJobsDashboard() {
    $("#nav-home").removeClass("blue");
    $("#nav-logs").removeClass("blue");
    $("#nav-dash").addClass("blue");
    $("#body-container").html("");

    $.ajax({
        url: "/flask/jobs",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            all_activities = JSON.parse(response)
            loadActivityCards("DESC");
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button fail");
            $("#confirmation").html("<span>&#10007</span> Jobs status check failed");
        }
    });
}

function loadActivityCards(order) {
    // order = string; if "ASC", the list of jobs is loaded in ascending order, if "DESC", in descending order
    $.get("../templates/jobCard.html", function(template) {
        $('<div id="dashboard" class="w3-container">').appendTo("#body-container");

        activities_length = Object.keys(all_activities).length

        if (order == "ASC") {
            for (i=0; i<activities_length; i++) {
                createActivityCard(template, i);
            }
        } else {
            for (i=activities_length-1; i>=0; i--) {
                createActivityCard(template, i);
            }
        }

        $('</div>').appendTo("#body-container");
    });
}

function createActivityCard(template, index) {
    var activity = all_activities["activity" + index];
    var card = $(template)[0];
    $(card).attr("id", "card_" + index);
    $(card).find("#cardTitle").html(activity.activity_name);

    try {
        machines = activity.machines;
    } catch(error) {
        machines = "PENDING..."
    }

    $(card).find("#cardBody").html("<p><b>Machines: </b>" + machines.join(", ") + "</p><p><b>Submitted on: </b>" + activity.date_submitted + "</p><p><b>No. Jobs: </b>" + activity.jobs + "</p>");
    $(card).find("#cardStatus").html(activity.status);
    $(card).find("#viewDetails").attr('onClick', "getJobDetails(" + index + ")")
    $("#dashboard").append(card);
}

function getJobDetails(index) {
    $("#nav-dash").removeClass("blue");
    activity = all_activities["activity" + index];

    $.ajax({
        url: "/flask/job/" + activity["activity_id"],
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            activity_jobs = JSON.parse(response);

            for (job in activity_jobs) { 
                $("#body-container").html(loadJobDetails(activity_jobs[job]));
            }

            if (($("#nav-home").hasClass("blue")) && (current_job.status !== "COMPLETED")) {
                setTimeout(getCurrentJobStatus, 5000);
            } else {
                console.log("finished");
            }
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Job status check failed");
        }
    });
}

function loadJobDetails(job) {
    var job_html = '<div class="jobDetails self-center">';
    job_html += '<div class="jobLine"><b>Machine: </b><div id="jobMachine">' + job.machine + '</div></div>';
    job_html += '<div class="jobLine"><b>Queue: </b><div id="jobQueue">' + job.queue + '</div></div>';
    job_html += '<div class="jobLine"><b>Date: </b><div id="jobSubmit">' + job.submit_time + '</div></div>';

    if (job.status == "QUEUED") {
        job_html += '<div class="jobLine"><b>Status: </b><button id="jobStatus" class="button amber self-right">' + job.status + '</button></div>';
    } else if (job.status == "RUNNING") {  
        job_html += '<div class="jobLine"><b>Status: </b><button id="jobStatus" class="button green self-right">' + job.status + '</button></div>';
    } else if (job.status == "ERROR") {
        job_html += '<div class="jobLine"><b>Status: </b><button id="jobStatus" class="button red self-right">' + job.status + '</button></div>';
    } else { 
        job_html += '<div class="jobLine"><b>Status: </b><button id="jobStatus" class="button blue self-right">' + job.status + '</button></div>';
    }

    job_html += '</div>';

    return job_html;
}

function getLogs() {
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logs").addClass("blue");
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

