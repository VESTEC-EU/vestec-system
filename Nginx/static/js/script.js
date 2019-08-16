var current_job = {};
var all_jobs = {}; 

$("#checkJobStatus").hide();

$(function(){
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
            all_jobs = JSON.parse(response);
            console.log(all_jobs);
            loadJobCards("DESC");
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button fail");
            $("#confirmation").html("<span>&#10007</span> Jobs status check failed");
        }
    });
}

function loadJobCards(order) {
    /* jobs = {activity0: {
                   activity_id: str(uuid4()),
                   activity_name: str,
                   date_submitted: 'mm/dd/yyyy, HH:MM:SS',
                   status: 'PENDING'/'ACTIVE'/'COMPLETED'/'ERROR',
                   activity_type: str,
                   location: str,
                   jobs: [
                       {job_id: str(uuid4()),
                        queue_id: str(uuid4()),
                        no_nodes: int,
                        work_directory: str,
                        executable: str, 
                        walltime: int, 
                        submit_time: 'dd/mm/yyyy, HH:MM:SS', 
                        run_time: 'HH:MM:SS', 
                        end_time: 'dd/mm/yyyy, HH:MM:SS', 
                        status: 'QUEUED'/'RUNNING'/'COMPLETED'/'ERROR', 
                        machine: str}
                   ]
              }
    */ 
    // order = string; if "ASC", the list of jobs is loaded in ascending order, if "DESC", in descending order
 
    $.get("../templates/jobCard.html", function(job_card) {
        $('<div id="dashboard" class="w3-container">').appendTo("#body-container");

        if (order == "ASC") {
            for (var i=0; i<all_jobs.length; i++) {
                var activity = all_jobs[i];
                var card = $(job_card)[0];
                $(card).attr("id", "card_" + i);
                $(card).find("header").html("<h3>" + activity.activity_name + "</h3>");
                $(card).find("#cardBody").html("<p>Machine: " + activity.jobs[0].machine + "</p><p>Status: " + activity.status + "</p>");
                $(card).find("footer").html("<h5>Submitted on " + activity.date_submitted + "</h5>");
                $("#dashboard").append(card);
            }
        } else {
            for (var i=all_jobs.length-1; i>=0; i--) {
                var activity = all_jobs[i];
                var card = $(job_card)[0];
                $(card).attr("id", "card_" + i);
                $(card).find("header").html("<h3>" + activity.activity_name + "</h3>");
                $(card).find("#cardBody").html("<p>Machine: " + activity.jobs[0].machine + "</p><p>Status: " + activity.status + "</p>");
                $(card).find("footer").html("<h5>Submitted on " + job.date + "</h5>");
                $("#dashboard").append(card);
            }
        }
        $('</div>').appendTo("#body-container");
    });
}


