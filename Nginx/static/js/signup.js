function signUp() {
    var user = {};
    user["username"] = $("#su-username").val();
    user["name"] = $("#su-name").val();
    user["email"] = $("#su-email").val();
    user["password"] = $("#su-password").val();
    user["confirm_pass"] = $("#su-confirm-pass").val();

    console.log(user);

    if (user["username"] && user["name"] && user["email"] && user["password"]) {
        if (user["password"] != user["confirm_pass"]) {
            $("#signup-form #confirm-pass").setCustomValidity("Sorry, passwords do not match.");
        }
        else {
            $.ajax({
                url: "/flask/signup",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify(user),
                dataType: "text",
                success: function(response) {
                    console.log(response);
                    if (response == "True") {
                        $("#login-message").html('<a href="/" class="blue-txt">User successfully created. Log in.</a>');
                        $("#login-message").show();
                    } else {
                        $("#login-message").html("User creation failed. Please try again.");
                        $("#login-message").show();
                    }
                },
                error: function(xhr) {
                    $("#login-message").html("User creation failed. Please try again.");
                    $("#login-message").show();
                }
            });
        }
    } else {
        console.log("The user details cannot be reached...");
    }
}
