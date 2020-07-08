function signUp() {
    var user = {};
    user["username"] = $("#su-username").val();
    user["name"] = $("#su-name").val();
    user["email"] = $("#su-email").val();
    user["password"] = $("#su-password").val();
    user["confirm_pass"] = $("#su-confirm-pass").val();

    if (user["username"] && user["name"] && user["email"] && user["password"]) {
        if (user["password"] != user["confirm_pass"]) {
            $("#login-message").html("The passwords do not match, please fix and retry");
            $("#login-message").removeClass().addClass("button white-btn amber-high-btn self-left");
            $("#login-message").show();
        } else {
            $.ajax({
                url: "/flask/signup",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify(user),
                dataType: "json",
                success: function(response) {
                    if (response.status == 200) {
                        $("#login-message").html('<a href="/" style="color: #4c904f;">' + response.msg + '</a>');
                        $("#login-message").removeClass().addClass("button white-btn green-high-btn self-left");
                        $("#login-message").show();
                    } else {
                        $("#login-message").html(response.msg);
                        $("#login-message").removeClass().addClass("button white-btn amber-high-btn self-left");
                        $("#login-message").show();
                    }
                },
                error: function(response) {
                    $("#login-message").html("Internal system error, signup failed");
                    $("#login-message").removeClass().addClass("button white-btn red-high-btn self-left");
                    $("#login-message").show();
                }
            });
        }
    } else {
        $("#login-message").html("Some details are missing, all are required");
        $("#login-message").removeClass().addClass("button amber-high-btn white-btn self-left");
        $("#login-message").show();
    }
}
