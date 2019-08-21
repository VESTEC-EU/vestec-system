var current_job = {};
var all_activities = {};

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
    var username = $("#login-container #username").val();
    var password = $("#login-container #password").val();

    $.ajax({
        url: "/flask/auth",
        type: "GET",
        success: function(response) {
            if (response == "real") {
                window.location.href = "/home";
            }
        },
        error: function(xhr) {
            $("#login-message").text("Username or password incorrect. Please try again.");
        }
    });
}

function getJobWizard() {
    $("#nav-dash").removeClass();
    $("#nav-home").addClass("blue");
    $("#body-container").load("../templates/createJobWizard.html");
}

function submitJob() {
    job = {}
    job["job_name"] = $("#userInput").val();

    if (job["job_name"] == "") {
        $("#confirmation").removeClass().addClass("button amber self-center");
        $("#confirmation").html("<span>&#9888</span> Please enter a job name");
        $("#confirmation").show();
    } else {
        $.ajax({
            url: "/flask/submit",
            type: "PUT",
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

function getCurrentJobStatus() {
    $.ajax({
        url: "/flask/jobs/current",
        type: "GET",
        success: function(response) {
            current_job = JSON.parse(response);
            var job_details = loadJobDetails();
            $("#body-container").html(job_details);

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

function loadJobDetails() {
    var job_html = '<div class="jobDetails">Name: <div id="jobName">' + current_job.Name + '</div></div><div class="jobDetails">Date: <div id="jobDate">' + current_job.date + '</div></div>';

    if (current_job.status == "PENDING") {
        job_html += '<div class="jobDetails">Status: <button id="jobStatus" class="button amber self-right">' + current_job.status + '</button></div>';
    } else if (current_job.status == "ACTIVE") {  
        job_html += '<div class="jobDetails">Status: <button id="jobStatus" class="button green self-right">' + current_job.status + '</button></div>';
    } else { 
        job_html += '<div class="jobDetails">Status: <button id="jobStatus" class="button blue self-right">' + current_job.status + '</button></div>';
    }

    return job_html;
}

function getJobsDashboard() {
    $("#nav-home").removeClass();
    $("#nav-dash").addClass("blue");
    $("#body-container").html("");

    $.ajax({
        url: "/flask/jobs",
        type: "GET",
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
    var activity = all_activities["activity" + i];
    var card = $(template)[0];
    $(card).attr("id", "card_" + i);
    $(card).find("header").html("<h3>" + activity.activity_name + "</h3>");

    try {
        machine = activity.jobs[0].machine;
    } catch(error) {
        machine = "PENDING..."
    }

    $(card).find("#cardBody").html("<p>Machine: " + machine + "</p><p>Status: " + activity.status + "</p>");
    $(card).find("footer").html("<h5>Submitted on " + activity.date_submitted + "</h5>");
    $("#dashboard").append(card);
}

