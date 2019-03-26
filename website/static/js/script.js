$("#checkJobStatus").hide();

function submitJob() {
    text = $("#userInput").val();

    $.ajax({
        url: "/submit",
        type: "PUT",
        data: {jsdata: text},
        success: function(response) {
            $("#confirmation").html(response);
            $("#checkJobStatus").show();
        },
        error: function(xhr) {
            $("#confirmation").html("Job submission failed");
        }
    });
}

function getJobStatus() {
    $.ajax({
        url: "/jobs/current",
        type: "GET",
        success: function() {
            window.location.href = "/jobs/current";
        },
        error: function(xhr) {
            $("#confirmation").html("Job status check failed");
        }
    });
}

function getAllJobsStatus(){
    $.ajax({
        url: "/jobs",
        type: "GET",
        success: function() {
            window.location.href = "/jobs";
        },
        error: function(xhr) {
            $("#confirmation").html("Jobs status check failed");
        }
    });
}