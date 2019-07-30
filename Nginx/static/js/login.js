$("#signup").click(function() {
    $("body").empty();
    $("body").load("../templates/signUp.html");
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

function signUp() {
    var user = {};
    user["username"] = $("#signup-form #username").val();
    user["name"] = $("#signup-form #name").val();
    user["email"] = $("#signup-form #email").val();
    user["password"] = $("#signup-form #password").val();
    user["confirm_pass"] = $("#signup-form #confirm-pass").val();

    if ((user["username"] != null) && (user["name"] != null) && (user["email"] != null) (user["password"] != null)) {
        if (user["password"] != user["confirm_pass"]) {
            $("#signup-form #confirm-pass").setCustomValidity("Sorry, passwords do not match.");
        }
        else {
            $.ajax({
                url: "/flask/signup",
                type: "POST",
                data: {jsdata: user},
                success: function(response) {
                    location.reload();
                    $("#confirmation").show();
                    $("#confirmation").removeClass().addClass("button green self-center");
                    $("#confirmation").html("User successfully created. Please try to log in.");
                },
                error: function(xhr) {
                    $("#confirmation").show();
                    $("#confirmation").removeClass().addClass("button red self-center");
                    $("#confirmation").html("User creation failed. Please try again.");
                }
            });
        }
    }
}
