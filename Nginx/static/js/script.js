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
    $("#body-container").load("../templates/createJobWizard.html");
}

function getJobsDashboard() {
    $("#body-container").load("../templates/dashboard.html");
}

function userLogin() {
    var username = $("#username").val();
    var password = $("#password").val();

    $.ajax({
        url: "/flask/auth",
        type: "GET",
        success: function(response) {
            if (response == "real") {
                window.location = "/base.html";
            }
        },
        error: function(xhr) {
            $("#login-message").text("Username or password incorrect. Please try again.");
        }
    });
}

function submitJob() {
    text = $("#userInput").val();

    if (text === "") {
        $("#confirmation").removeClass().addClass("button warning");
        $("#confirmation").html("<span>&#9888</span> Please enter a job name");
    } else {
        $.ajax({
            url: "/flask/submit",
            type: "PUT",
            data: {jsdata: text},
            success: function(response) {
                $("#userInput").val('');
                $("#confirmation").removeClass().addClass("button success");
                $("#confirmation").html("<span>&#10003</span> Job successfully submitted");
                $("#checkJobStatus").show();
            },
            error: function(xhr) {
                $("#confirmation").removeClass().addClass("button fail");
                $("#confirmation").html("<span>&#10007</span> Job submission failed");
            }
        });
    }
}

function getJobStatus() {
    $.ajax({
        url: "/flask/jobs/current",
        type: "GET",
        success: function() {
            window.location.href = "/jobs/current";
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button fail");
            $("#confirmation").html("<span>&#10007</span> Job status check failed");
        }
    });
}

function getAllJobsStatus(){
    $.ajax({
        url: "/flask/jobs",
        type: "GET",
        success: function() {
            window.location.href = "/jobs";
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button fail");
            $("#confirmation").html("<span>&#10007</span> Jobs status check failed");
        }
    });
}
