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

function getJobWizard() {
    $("#nav-dash").removeClass();
    $("#nav-home").addClass("blue");
    $("#body-container").load("../templates/createJobWizard.html");
}

function submitJob() {
    text = $("#userInput").val();

    if (text === "") {
        $("#confirmation").removeClass().addClass("button amber self-center");
        $("#confirmation").html("<span>&#9888</span> Please enter a job name");
        $("#confirmation").show();
    } else {
        $.ajax({
            url: "/flask/submit",
            type: "PUT",
            data: {jsdata: text},
            success: function(response) {
                $("#userInput").val('');
                $("#confirmation").show();
                $("#confirmation").removeClass().addClass("button green self-center");
                $("#confirmation").html("<span>&#10003</span> Job successfully submitted");
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
            loadJobCards("DESC");
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button fail");
            $("#confirmation").html("<span>&#10007</span> Jobs status check failed");
        }
    });
}

function loadJobCards(order) {
    // jobs = json of jobs resulted from getJobsDashboard GET request
    // order = string; if "ASC", the list of jobs is loaded in ascending order, if "DESC", in descending order
 
    $.get("../templates/jobCard.html", function(job_card) {
        $('<div id="dashboard" class="w3-container">').appendTo("#body-container");

        if (order == "ASC") {
            for (var i=0; i<all_jobs.length; i++) {
                var job = all_jobs[i];
                var card = $(job_card)[0];
                $(card).attr("id", "card_" + i);
                $(card).find("header").html("<h3>" + job.Name + "</h3>");
                $(card).find("#cardBody").html("<p>Machine: " + job.jobs[0].machine + "</p><p>Status: " + job.jobs[0].status + "</p>");
                $(card).find("footer").html("<h5>Submitted on " + job.date + "</h5>");
                $("#dashboard").append(card);
            }
        } else {
            for (var i=all_jobs.length-1; i>=0; i--) {
                var job = all_jobs[i];
                var card = $(job_card)[0];
                $(card).attr("id", "card_" + i);
                $(card).find("header").html("<h3>" + job.Name + "</h3>");
                $(card).find("#cardBody").html("<p>Machine: " + job.jobs[0].machine + "</p><p>Status: " + job.jobs[0].status + "</p>");
                $(card).find("footer").html("<h5>Submitted on " + job.date + "</h5>");
                $("#dashboard").append(card);
            }
        }
        $('</div>').appendTo("#body-container");
    });
}


