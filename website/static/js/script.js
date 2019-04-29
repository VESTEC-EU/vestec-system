$("#checkJobStatus").hide();

$("#userInput").keyup(function(e) {
    if (e.keyCode == 13) {
        submitJob();
    }
});

function submitJob() {
    text = $("#userInput").val();

    if (text === "") {
        $("#confirmation").removeClass().addClass("button warning");
        $("#confirmation").html("<span>&#9888</span> Please enter a job name");
    } else {
        $.ajax({
            url: "/submit",
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
        url: "/jobs/current",
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
        url: "/jobs",
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