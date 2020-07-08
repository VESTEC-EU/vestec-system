var all_activities = {};
var user_type=-1;
var version_number=-1;

var add_data_dialog;
var edit_data_dialog;
var edit_user_dialog;

const ConfirmationTypeEnum = Object.freeze({"DELETEEDIHANDLER":1, "DELETEDATAITEM":2, "DELETEUSER":3, "CANCELSIMULATION":4, "DELETEMACHINE":5});
var confirmation_box_type=null;
var confirmation_box_data={};

$( function() {
    add_data_dialog = $("#add-data-dialog-form").dialog({
    autoOpen: false,
    height: 450,
    width: 500,
    modal: true,
    buttons: {
        "Add data": addProvidedData,
        Cancel: function() {
            add_data_dialog.dialog( "close" );
        }
    },
    close: function() {        
        
    }
    });
    
    $( "#dialog-message" ).dialog({
        modal: true,
        autoOpen: false,
        height: "auto",
        width: "auto",
        buttons: {
            Ok: function() {
              $( this ).dialog( "close" );
            }
        }
    });      

    edit_data_dialog = $("#edit-data-dialog-form").dialog({
        autoOpen: false,
        height: 450,
        width: 500,
        modal: true,
        buttons: {
            "Edit data": editProvidedData,
            Cancel: function() {
                edit_data_dialog.dialog( "close" );
            }
        },
        close: function() {        
            
        }
        });
   
        $( "#dialog-confirm" ).dialog({
          resizable: false,
          autoOpen: false,
          height: "auto",
          width: 400,
          modal: true,
          buttons: {
            "OK": function() {
              $( this ).dialog( "close" );
              if (confirmation_box_type == ConfirmationTypeEnum.DELETEEDIHANDLER) {
                performHandlerDeletion();
              } else if (confirmation_box_type == ConfirmationTypeEnum.DELETEDATAITEM) {
                performDataSetDeletion();
              } else if (confirmation_box_type == ConfirmationTypeEnum.DELETEUSER) {
                performUserDeletion();
              } else if (confirmation_box_type == ConfirmationTypeEnum.CANCELSIMULATION) {
                performSimulationCancel();
              } else if (confirmation_box_type == ConfirmationTypeEnum.DELETEMACHINE) {
                performMachineDelete();
              }
            },
            Cancel: function() {
              $( this ).dialog( "close" );
            }
          }
        });

        edit_user_dialog = $("#edit-user-dialog-form").dialog({
            autoOpen: false,
            height: 720,
            width: 500,
            modal: true,
            buttons: {                
                Cancel: function() {
                    edit_user_dialog.dialog( "close" );
                }
            },
            close: function() {        
                
            }
            });            

        edit_machine_dialog = $("#edit-machine-dialog-form").dialog({
                autoOpen: false,
                height: "auto",
                width: 500,
                modal: true,
                buttons: {     
                    "OK": function() {
                        performAddMachine();                        
                    },
                    Cancel: function() {
                        edit_machine_dialog.dialog( "close" );
                    }
                },
                close: function() {        
                    
                }
                }); 
    });



function performDataSetDeletion() {
    url_append="data_uuid="+confirmation_box_data["data_uuid"]+"&incident_uuid="+confirmation_box_data["incident_uuid"];
    $.ajax({
        url: "/flask/data?"+url_append,
        type: "DELETE",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},        
        success: function(response) {
            getIncidentDetails(confirmation_box_data["incident_uuid"]);
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User edit failed");
        }
    });
}

function performHandlerDeletion() {
    $.ajax({
        url: "/flask/deleteedihandler",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(confirmation_box_data),
        dataType: "json",
        success: function(response) {
            getEDIInfo();
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User edit failed");
        }
    });
}

function checkAuth() {
    // need to add a check to flask to see if the token in the session is the same as the current user's
    var jwt_token = sessionStorage.getItem("access_token");

    if (typeof jwt_token === 'undefined' || jwt_token === null || jwt_token === '') {
        window.location.href = "/login";
    } else {
        $.ajax({
            url: "/flask/authorised",
            type: "GET",
            headers: {'Authorization': 'Bearer ' + jwt_token},
            success: function(response) {
                if (response.status == 200) {                    
                    $("#mainbody").load("../templates/loggedin.html", function() {
                        getJobsDashboard();
                        generateNavigationBar();
                        setVersionNumber();
                    });                    
                } else {
                    window.location.href = "/login";
                }
            },
            error: function(xhr) {
                window.location.href = "/login";
            }
        });
    }
}

function checkAuthStillValid() {
    var jwt_token = sessionStorage.getItem("access_token");

    if (typeof jwt_token === 'undefined' || jwt_token === null || jwt_token === '') {
        window.location.href = "/login";
    } else {
        $.ajax({
            url: "/flask/authorised",
            type: "GET",
            headers: {'Authorization': 'Bearer ' + jwt_token},
            success: function(response) {
                if (response.status != 200) {                    
                    window.location.href = "/login";
                }
            },
            error: function(xhr) {
                window.location.href = "/login";
            }
        });
    }
}

$("#checkJobStatus").hide();
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
        $("#login-message").html("Please enter a username and password.");
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
                    $("#login-message").html(response.msg);
                    $("#login-message").removeClass().addClass("button white-btn red-high-btn self-left");
                    $("#login-message").show();
                }
            },
            error: function(xhr) {
                $("#login-message").html("Internal system error, consult the logs for more details");
                $("#login-message").removeClass().addClass("button white-btn red-high-btn self-left");
                $("#login-message").show();
            }
        });
    }
}

function getJobWizard() {
    checkAuthStillValid();
    $("#nav-home").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#nav-dash").addClass("blue");
    $("#body-container").load("../templates/createJobWizard.html", function() {
    $.ajax({
        url: "/flask/getmyworkflows",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {            
            var workflows = JSON.parse(response.workflows);
            console.log(workflows);
            $("#incidentType").empty();
            for (item in workflows) {
                item = workflows[item];                                                   
                $("#incidentType").append("<option value='"+item+"'>"+item+"</option>");                
            }            
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User workflow lookup failed");
        }
    });
    });
}

function submitJob() {
    checkAuthStillValid();
    var job = {}
    job["kind"] = $("#incidentType").val();
    job["name"] = $("#incidentName").val();
    if ($("#upperLeftLatlong").val().length > 0) job["upperLeftLatlong"] = $("#upperLeftLatlong").val();
    if ($("#lowerRightLatlong").val().length > 0) job["lowerRightLatlong"] = $("#lowerRightLatlong").val();
    if ($("#duration").val().length > 0) job["duration"] = $("#duration").val();
    
    $.ajax({
        url: "/flask/createincident",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(job),
        dataType: "json",
        success: function(response) {
            if (response.status == "201") {
                $("#userInput").val('');
                $("#confirmation").html("<span>&#10003</span>" + response.msg);
                $("#confirmation").removeClass().addClass("button white-btn green-high-btn self-center");
                $("#confirmation").show();
            } else {
                $("#confirmation").html("<span>&#10007</span>" + response.msg);
                $("#confirmation").removeClass().addClass("button white-btn amber-high-btn self-center");
                $("#confirmation").show();
            }
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error creating new incident");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function setVersionNumber() {
    if (version_number == -1) {
        $.ajax({
            url: "/flask/version",
            type: "GET",
            headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
            success: function(response) {
              if (response.status == 200) {
                version_number = response.version;
                $("#systemversioninfo").text("System version "+version_number)
              } else {
                console.log({"status": 400, "msg": "Error with the look up version number"});
              }
            },
            error: function(xhr) {
              console.log({"status": 500, "msg": "Error with the look up version number"});
            }
          });
      } else {
        $("#systemversioninfo").text("System version "+version_number)
      }
}

function generateNavigationBar() {
  var html_code="<div id=\"nav-home\" class=\"blue menu_item\" onClick=\"getJobsDashboard()\">Home</div>\<div id=\"nav-dash\" class=\"menu_item\" onClick=\"getJobWizard()\">New incident</div>"
  html_code+="<div id=\"nav-logout\" class=\"self-right menu_item\" onClick=\"logOut()\">Log Out</div>"
  // We store the user type to avoid hitting the server, as the activities are also protected on the server then at worst a user could
  // force the menu to display but couldn't action any of the activities under it
  if (user_type == -1) {
    $.ajax({
      url: "/flask/user_type",
      type: "GET",
      headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
      success: function(response) {
        if (response.status == 200) {
          user_type = JSON.parse(response.access_level);
          generateNavigationBar();
        } else {
          console.log({"status": 400, "msg": "Internal system error, can not retrieve user authorisation level"});
        }
      },
      error: function(xhr) {
        console.log({"status": 500, "msg": "Internal system error, consult the logs for more details"});
      }
    });
    user_type
  } else if (user_type > 0) {
    html_code+=generateAdminDropdown();
  }
  $("#navigation_bar").html(html_code);  
}

function generateAdminDropdown() {
  var admin_html="<div class=\"admin_dropdown\">";
  admin_html+="<button class=\"dropbtn\">Admin<i class=\"fa fa-caret-down\"></i></button>";
  admin_html+="<div class=\"admin_dropdown_content\">";
  admin_html+="<div class=\"admin_item\" onClick=\"getLogs()\">Logs</div>";
  admin_html+="<div class=\"admin_item\" onClick=\"getSystemHealth()\">System health</div>";
  admin_html+="<div class=\"admin_item\" onClick=\"getWorkflows()\">Workflows</div>";
  admin_html+="<div class=\"admin_item\" onClick=\"getUsers()\">Users</div>";
  admin_html+="<div class=\"admin_item\" onClick=\"getEDIInfo()\">EDI</div>";
  admin_html+="<div class=\"admin_item\" onClick=\"getMachineInfo()\">Machines</div>";
  admin_html+="</div></div>";
  return admin_html;
}

function getJobsDashboard() {
    checkAuthStillValid();
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#nav-home").addClass("blue");    

    pending_filter=getDashboardFilterValue("pending_incidents", true);
    active_filter=getDashboardFilterValue("active_incidents", true);
    completed_filter=getDashboardFilterValue("completed_incidents", false);
    cancelled_filter=getDashboardFilterValue("cancelled_incidents", false);
    error_filter=getDashboardFilterValue("error_incidents", false);
    archived_filter=getDashboardFilterValue("archived_incidents", false);
    $("#body-container").html("");

    http_args=""
    if (pending_filter) http_args+="pending=true"
    if (active_filter) http_args+=(http_args.length > 0 ? "&" : "") + "active=true"
    if (completed_filter) http_args+=(http_args.length > 0 ? "&" : "") + "completed=true"
    if (cancelled_filter) http_args+=(http_args.length > 0 ? "&" : "") + "cancelled=true"
    if (error_filter) http_args+=(http_args.length > 0 ? "&" : "") + "error=true"
    if (archived_filter) http_args+=(http_args.length > 0 ? "&" : "") + "archived=true"

    $.ajax({
        url: "/flask/getincidents?"+http_args,
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},        
        success: function(response) {
            if (response.status == 200) {
                all_incidents = JSON.parse(response.incidents);
                loadIncidentCards(all_incidents, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter);
            } else {
                console.log({"status": 400, "msg": "Internal system error, cannot extract activities."});
            }
        },
        error: function(xhr) {
            console.log({"status": 500, "msg": "Internal system error, consult the logs for more details"});
        }
    });
}

function getDashboardFilterValue(identifier, default_val) {    
    if ($("#"+identifier).length) return $('#'+identifier).prop("checked");
    return default_val;
}

function generateDashboardFilterBar(pending_checked, active_checked, completed_checked, cancelled_checked, error_checked, archived_checked) {
    var filter_bar = '<div class="jobDetails self-center" style="display: flex;">';
    filter_bar+='<div style="margin-right: 10px;"><input type="checkbox" id="pending_incidents" ';
    if (pending_checked) filter_bar+="checked ";
    filter_bar+='onclick="getJobsDashboard()"><label for="pending_incidents">Pending</label></div>';
    filter_bar+='<div style="margin-right: 10px;"><input type="checkbox" id="active_incidents" ';
    if (active_checked) filter_bar+="checked ";    
    filter_bar+='onclick="getJobsDashboard()"><label for="active_incidents">Active</label></div>';    
    filter_bar+='<div style="margin-right: 10px;"><input type="checkbox" id="completed_incidents" ';
    if (completed_checked) filter_bar+="checked ";    
    filter_bar+='onclick="getJobsDashboard()"><label for="completed_incidents">Completed</label></div>';    
    filter_bar+='<div style="margin-right: 10px;"><input type="checkbox" id="cancelled_incidents" ';
    if (cancelled_checked) filter_bar+="checked ";    
    filter_bar+='onclick="getJobsDashboard()"><label for="cancelled_incidents">Cancelled</label></div>';
    filter_bar+='<div style="margin-right: 10px;"><input type="checkbox" id="error_incidents" ';
    if (error_checked) filter_bar+="checked ";    
    filter_bar+='onclick="getJobsDashboard()"><label for="error_incidents">Error</label></div>';
    filter_bar+='<div style="margin-right: 10px;"><input type="checkbox" id="archived_incidents" ';
    if (archived_checked) filter_bar+="checked ";    
    filter_bar+='onclick="getJobsDashboard()"><label for="archived_incidents">Archived</label></div>';
    filter_bar+="</div>";
    return filter_bar;
}

function loadIncidentCards(incidents, pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter) {
    // order = string; if "ASC", the list of jobs is loaded in ascending order, if "DESC", in descending order
    $.get("../templates/jobCard.html", function(template) {
        $('<div id="dashboard" class="w3-container">').appendTo("#body-container");

        
        $("#dashboard").append(generateDashboardFilterBar(pending_filter, active_filter, completed_filter, cancelled_filter, error_filter, archived_filter));

        for (incident in incidents) {
            createIncidentCard(template, incidents[incident]);
        }

        $('</div>').appendTo("#body-container");
    });
}

function createIncidentCard(template, incident) {    
    var card = $(template)[0];
    //$(card).attr("id", "card_" + index);
    $(card).find("#cardTitle").html(incident.name);
    
    $(card).find("#cardBody").html("<p><b>Kind: </b>" + incident.kind + "</p><p><b>Incident on: </b>" + incident.incident_date + "</p><p><b>Created by: </b>" + incident.creator+"</p>");
    $(card).find("#cardStatus").html(incident.status);
    $(card).find("#viewDetails").attr('onClick', "getIncidentDetails(\"" + incident.uuid + "\")");
    $(card).find("#cardTitle").attr('onClick', "getIncidentDetails(\"" + incident.uuid + "\")");
    $("#dashboard").append(card);
}

function getIncidentDetails(incident_uuid) {
    $("#nav-home").removeClass("blue");    

    $.ajax({
        url: "/flask/incident/" + incident_uuid,
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            incident_details = JSON.parse(response.incident);            
            $("#body-container").html(loadIncidentDetails(incident_details));           
            var viz = new Viz();
            viz.renderSVGElement(incident_details.digraph).then(function(element) {
                $("svg").append(element);
                $("#workflow_diagram").html($("#workflow_diagram").html());
            });
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Incident detail retrieval failed");
        }
    });
}

function addDataForIncident(incidentID, incidentQueueName) {    
    $('#add-data-dialog-contents').load('templates/adddata.html #addDataScreen', function() {
        $('#dataIncidentId').val(incidentID);
        $('#dataQueue').val(incidentQueueName);        
        add_data_dialog.dialog( "open" );
    });    
}

function addProvidedData() {
    const reader = new FileReader()

    reader.onload = function () {        
        var wf = {};        
        wf["filename"] = $('#fileToUpload').val().split('\\').pop();
        wf["filetype"] = $('#filetype').val();
        wf["filecomment"] = $('#filecomment').val();
        wf["incidentId"] = $('#dataIncidentId').val();
        wf["payload"] = reader.result;
        $.ajax({
            url: "/EDI/"+$('#dataQueue').val()+$('#dataIncidentId').val(),
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(wf),
            dataType: "json",
            success: function(response) {
                add_data_dialog.dialog( "close" );
            },
            error: function(response) {
                $("#confirmation").html("<span>&#10007</span> Error adding workflow");
                $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
                $("#confirmation").show();
            }
        });        
    };
        
    reader.readAsDataURL($('#fileToUpload').prop('files')[0])
}

function testIncident(incidentID) {
    var wf = {}; 
    wf["data"]="Test from the web-UI"
    $.ajax({
        url: "/EDI/test_stage_"+incidentID,
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            $('#test_workflow').prop('disabled', true);
            $('#test_workflow').removeClass('blue');
            setTimeout(function() {
                $('#test_workflow').prop('disabled', false);
                $('#test_workflow').addClass('blue');
            }, 5000);
        },
        error: function(response) {            
        }
    }); 
}

function loadIncidentDetails(incident) {
    var incident_html = '<div class="jobDetails self-center">';
    incident_html += '<div class="jobLine"><b>UUID: </b><div>' + incident.uuid + '</div></div>';
    incident_html += '<div class="jobLine"><b>Name: </b><div>' + incident.name + '</div></div>';
    incident_html += '<div class="jobLine"><b>Kind: </b><div>' + incident.kind + '</div></div>';
    incident_html += '<div class="jobLine"><b>Created On: </b><div>' + incident.incident_date + '</div></div>';
    incident_html += '<div class="jobLine"><b>Created By: </b><div>' + incident.creator + '</div></div>';
    incident_html += '<div class="jobLine"><b>Status: </b><div>' + incident.status + '</div></div>';
    if ("upper_left_latlong" in incident) {
        incident_html += '<div class="jobLine"><b>Upper left Lat/Long: </b><div>' + incident.upper_left_latlong + '</div></div>';
    }
    if ("lower_right_latlong" in incident) {
        incident_html += '<div class="jobLine"><b>Lower right Lat/Long: </b><div>' + incident.lower_right_latlong + '</div></div>';
    }
    incident_html += '<div class="jobLine"><b>Associated datasets: </b><div>' + incident.data_sets.length + '</div></div>';
    incident_html += '<div class="jobLine"><b>Associated data transfers: </b><div>' + incident.data_transfers.length + '</div></div>';
    if (incident.status == "COMPLETE") {
        incident_html += '<div class="jobLine"><b>Completed On: </b><div>' + incident.date_completed + '</div></div>';
    }

    incident_html += '</div>';
    if (incident.status != "ARCHIVED") {
        incident_html+='<div class="jobDetails self-center">';
        if (incident.status == "PENDING") {
            incident_html += "<button class=\"button blue self-center\" onClick=\"activateIncident(\'"+incident.uuid+"\')\">Activate Incident</button>";
        }
        if (incident.status == "PENDING" || incident.status == "ACTIVE") {
            incident_html += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<button class=\"button blue self-center\" onClick=\"cancelIncident(\'"+incident.uuid+"\')\">Cancel Incident</button>";
        }
        if (incident.status == "COMPLETE" || incident.status == "CANCELLED") {
            incident_html += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<button class=\"button blue self-center\" onClick=\"archiveIncident(\'"+incident.uuid+"\')\">Archive Incident</button>";
        }

        if (incident.status == "ACTIVE" && incident.data_queue_name.length > 0) {
            incident_html += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<button class=\"button blue self-center\" onClick=\"addDataForIncident('"+incident.uuid+"','"+incident.data_queue_name+"')\">Add data</button>";
        }

        if (incident.status == "ACTIVE" && incident.test_workflow) {
            incident_html += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<button id=\"test_workflow\" class=\"button blue self-center\" onClick=\"testIncident('"+incident.uuid+"')\">Initiate test stage</button>";
        }
        
        incident_html += "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<button class=\"button blue self-center\" style=\"float: right;\" onClick=\"getIncidentDetails(\'"+incident.uuid+"\')\">Refresh Status</button></div>";
    }

    if (incident.simulations.length > 0) {
        incident_html+="<div id=\"incident_data\" class=\"jobDetails self-center\"><table id='incidentSimulationsTable' class='self-center displayTable'>";
        incident_html+="<thead><tr><th>Kind</th><th>Created</th><th>Status</th><th>Walltime</th><th>Number nodes</th><th>Machine</th><th>Job ID</th><th>Actions</th></tr></thead>";
        for (sim of incident.simulations) {    
            incident_html+="<td>"+sim.kind+"</td><td>"+sim.created+"</td><td>";
            if (sim.status_message != null) {
                incident_html+="<span class=\"link\" onclick=\"displayInfoMessage('"+sim.status_message+"');\">";
            }
            incident_html+=sim.status;
            if (sim.status_message != null) incident_html+="</span>";
            incident_html+=" <i>("+sim.status_updated+")</i></td><td>";            
            if (sim.walltime != null && sim.walltime != "" && (sim.status!="QUEUED" || sim.status!="PENDING" || sim.status!="CREATED")) {
                incident_html+=sim.walltime;
            } else {
                incident_html+=sim.requested_walltime;
            }
            incident_html+="</td><td>"+sim.num_nodes+"</td><td>";
            if ("machine" in sim) {
                incident_html+=sim.machine;
            }
            incident_html+="</td><td>";
            if ("jobID" in sim) {
                incident_html+=sim.jobID;
            }
            incident_html+="</td><td>";
            if (sim.status != "COMPLETED" && sim.status != "CANCELLED" && sim.status != "ERROR") {
                incident_html+="<img id='refresh_icon_"+sim.uuid+"' src='../img/refresh.png' class='click_button' width=26 height=26 title='Refresh status' onClick=\"refreshSimulation('"+sim.uuid+"','"+incident.uuid+"')\">";
            }
            if (sim.status=="QUEUED" || sim.status=="RUNNING" || sim.status=="PENDING" || sim.status=="CREATED") {                
                incident_html+="&nbsp;&nbsp;&nbsp;&nbsp;";
                incident_html+="<img src='../img/cross.png' class='click_button' width=26 height=26 title='Cancel simulation' onClick=\"cancelSimulation('"+sim.uuid+"','"+incident.uuid+"')\">";
            }
            incident_html+="</td></tr>";
        }
        incident_html+="</table></div>";
    }

    if (incident.data_sets.length > 0) {
        incident_html+="<div id=\"incident_data\" class=\"jobDetails self-center\"><table id='incidentDataTable' class='self-center displayTable'>";
        incident_html+="<thead><tr><th>Filename</th><th>File type</th><th>Location</th><th>Date Created</th><th>Actions</th></tr></thead>";        
        for (data_set of incident.data_sets) {
            locally_held=data_set.machine == "localhost";
            machine_name=locally_held ? "VESTEC system" : data_set.machine;
            incident_html+="<tr><td>"+data_set.name+"</td><td>"+data_set.type+"</td><td>"+machine_name+"</td><td>"+data_set.date_created+"</td><td>";
            if (locally_held) {
                incident_html+="<img src='../img/download.png' class='click_button' title='Download dataset' width=26 height=26 onClick=\"downloadData('"+data_set.uuid+"','"+data_set.name+"')\">";
                incident_html+="&nbsp;&nbsp;&nbsp;";
            }
            incident_html+="<img src='../img/edit.png' class='click_button' width=26 height=26 onClick=\"editDataItem('"+data_set.uuid+"','"+incident.uuid+"')\">";
            incident_html+="&nbsp;&nbsp;&nbsp;";
            incident_html+="<img src='../img/cross.png' class='click_button' width=26 height=26 onClick=\"deleteDataItem('"+data_set.uuid+"','"+incident.uuid+"')\">";
            incident_html+="</td></tr>";
        }
        incident_html+="</table></div>";
    }

    if (incident.data_transfers.length > 0) {
        incident_html+="<div id=\"incident_data_transfers\" class=\"jobDetails self-center\"><table id='incidentDataTransferTable' class='self-center displayTable'>";
        incident_html+="<thead><tr><th>File Transfer Started</th><th>Filename</th><th>Size</th><th>From</th><th>To</th><th>Status</th><th>Completed</th><th>Duration</th><th>Speed</th></tr></thead>";
        for (data_transfer of incident.data_transfers) {
            incident_html+="<tr>";
            incident_html+="<td>"+data_transfer.date_started+"</td>";
            incident_html+="<td>"+data_transfer.filename+"</td>";
            incident_html+="<td>"+data_transfer.size+"</td>";
            incident_html+="<td>"+data_transfer.src_machine+"</td>";
            incident_html+="<td>"+data_transfer.dst_machine+"</td>";
            incident_html+="<td>"+data_transfer.status+"</td>";
            incident_html+="<td>"+data_transfer.date_completed+"</td>";
            incident_html+="<td>"+data_transfer.completion_time+"</td>";
            incident_html+="<td>"+data_transfer.speed+"</td>";
            incident_html+="</tr>"
        }
        incident_html+="</table></div>";
    }

    incident_html+="<div id=\"workflow_diagram\" class=\"jobDetails self-center\"><svg id=\"svg-canvas\" style='width: 100%; height: auto;'></svg></div>"

    return incident_html;
}

function displayInfoMessage(message) {
    $("#dialog-message-text").text(message);
    $( "#dialog-message" ).dialog("open");    
}

function refreshSimulation(sim_uuid, incident_uuid) {
    var data_description = {};
    data_description["sim_uuid"] = sim_uuid;
    $('#refresh_icon_'+sim_uuid).css('opacity', 0.2);
    $.ajax({
        url: "/flask/refreshsimulation",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},   
        contentType: "application/json",
        data: JSON.stringify(data_description),
        dataType: "json",     
        success: function(response) {
            getIncidentDetails(incident_uuid);
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Simulation refresh failed");
        }
    });
}

function cancelSimulation(sim_uuid, incident_uuid) {
    confirmation_box_type=ConfirmationTypeEnum.CANCELSIMULATION;
    confirmation_box_data={"sim_uuid" : sim_uuid, "incident_uuid" : incident_uuid};
    $("#dialog-confirm-text").text("Are you sure you want to cancel this simulation?");
    $( "#dialog-confirm" ).dialog("open");
}

function performSimulationCancel() {    
    $.ajax({
        url: "/flask/simulation?sim_uuid="+confirmation_box_data["sim_uuid"],
        type: "DELETE",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},        
        success: function(response) {
            getIncidentDetails(confirmation_box_data["incident_uuid"]);
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Simulation cancel failed");
        }
    });   
}

function editDataItem(data_uuid, incident_uuid) {
    $.ajax({
        url: "/flask/metadata?data_uuid="+data_uuid+"&incident_uuid="+incident_uuid,
        type: "GET",
        contentType: "application/json",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},        
        success: function (response) {    
            meta_data = response.metadata;        
            $('#edit-data-dialog-contents').load('templates/editdata.html #editDataScreen', function() {
                $('#incidentId').val(incident_uuid);
                $('#dataId').val(data_uuid);
                $('#edit-filetype').val(meta_data.type);
                $('#edit-filecomment').val(meta_data.comment);
                edit_data_dialog.dialog( "open" );
            });  
        }
    });    
}

function editProvidedData() {
    var data_description = {};
    data_description["incident_uuid"] = $("#incidentId").val();
    data_description["data_uuid"] = $("#dataId").val();
    data_description["type"] = $("#edit-filetype").val();
    data_description["comments"] = $("#edit-filecomment").val();
    $.ajax({
        url: "/flask/metadata",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(data_description),
        dataType: "json",
        success: function(response) {
            edit_data_dialog.dialog( "close" );
            getIncidentDetails($("#incidentId").val());
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error adding workflow");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function deleteDataItem(data_uuid, incident_uuid) {
    confirmation_box_type=ConfirmationTypeEnum.DELETEDATAITEM;
    confirmation_box_data={"data_uuid" : data_uuid, "incident_uuid" : incident_uuid};
    $("#dialog-confirm-text").text("Are you sure you want to delete this data set?");
    $( "#dialog-confirm" ).dialog("open");
}

function downloadData(data_uuid, filename) {
    $.ajax({
        url: "/flask/data/"+data_uuid,
        type: "GET",
        dataType: 'binary',
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},        
        success: function (data) {            
            var url = URL.createObjectURL(data);
            var $a = $('<a />', {
                'href': url,
                'download': filename,
                'text': "click"
            }).hide().appendTo("body")[0].click(); 
            setTimeout(function() {
                URL.revokeObjectURL(url);
            }, 10000);           
        }
    }); 
}

function cancelIncident(incident_uuid) {
    $.ajax({
        url: "/flask/incident/"+incident_uuid,
        type: "DELETE",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",        
        success: function(response) {
            getIncidentDetails(incident_uuid);
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error cancelling incident");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function archiveIncident(incident_uuid) {    
    $.ajax({
        url: "/flask/archiveincident/"+incident_uuid,
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",        
        success: function(response) {
            getIncidentDetails(incident_uuid);
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error archiving incident");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function activateIncident(incident_uuid) {    
    $.ajax({
        url: "/flask/activateincident/"+incident_uuid,
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",        
        success: function(response) {
            getIncidentDetails(incident_uuid);
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error activating incident");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function createWorkflow() {
    var wf = {};
    wf["kind"] = $("#workflowname").val();
    wf["initqueuename"] = $("#workflowqueuename").val();
    wf["dataqueuename"] = $("#manualdataqueuename").val();
    wf["testworkflow"] = $("#test_workflow").is(':checked');
    $.ajax({
        url: "/flask/addworkflow",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            getWorkflows();
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error adding workflow");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function deleteWorkflow(kind) {
    var wf = {};
    wf["kind"] = kind;
    $.ajax({
        url: "/flask/deleteworkflow",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            getWorkflows();
        },
        error: function(response) {
            $("#confirmation").html("<span>&#10007</span> Error removing workflow");
            $("#confirmation").removeClass().addClass("button white-btn red-high-btn self-center");
            $("#confirmation").show();
        }
    });
}

function getWorkflows() {
    checkAuthStillValid();
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/workflows.html", function() {
        $.ajax({
            url: "/flask/workflowinfo",
            type: "GET",
            headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
            success: function(response) {
                var workflows = JSON.parse(response.workflows);
                $("#workflowTable").append("<tbody>");

                for (item in workflows) {
                    var wf_entry = "<tr>";
                    item = workflows[item];
                    wf_entry += "<td>" + item.kind + "</td>";
                    wf_entry += "<td>" + item.initqueuename + "</td>";
                    wf_entry += "<td>" + item.dataqueuename + "</td>";
                    wf_entry += "<td><img src='../img/cross.png' class='click_button' width=32 height=32 onClick=\"deleteWorkflow('"+item.kind+"')\"></td>";
                    
                    wf_entry += "</tr>";

                    $("#workflowTable").append(wf_entry);
                }
                $("#workflowTable").append("</tbody>");
            },
            error: function(xhr) {
                $("#confirmation").removeClass().addClass("button red self-center");
                $("#confirmation").html("<span>&#10007</span> Workflow retrieval failed");
            }
        });
    });
}

function getMachineInfo() {
    checkAuthStillValid();
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/machineinfo.html", function() {
        $.ajax({
            url: "/flask/getmachinestatuses",
            type: "GET",
            headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},        
            success: function(response) {
                var machine_infos = response.machine_statuses;
                $("#MachineInfotable").append("<tbody>");

                for (machine_info in machine_infos) {
                    var handler_entry = "<tr>";
                    item = machine_infos[machine_info];
                    handler_entry += "<td>"+item.name + "</td>";
                    handler_entry += "<td>"+item.host_name + "</td>";
                    handler_entry += "<td>"+item.connection_type + "</td>";                    
                    handler_entry += "<td>"+item.scheduler + "</td>";
                    handler_entry += "<td>"+parseInt(item.nodes) * parseInt(parseInt(item.cores_per_node)) + "</td>";
                    handler_entry += "<td>";

                    if ("status" in item && "status_last_checked" in item) {
                        handler_entry += item.status+"<i>&nbsp;&nbsp;("+item.status_last_checked+")</i>";
                    } else if ("status" in item) {
                        handler_entry += item.status;
                    } else {
                        handler_entry += "unknown";                    
                    }

                    handler_entry += "</td><td>";                    
                    if (item.enabled) {
                        handler_entry += "<img src='../img/enabled_icon.png' onclick=\"disableMachine('"+item.uuid+"')\" height='24' title='Disable machine' style='cursor: pointer;'>";
                    } else {
                        handler_entry += "<img src='../img/disabled_icon.png' onclick=\"enableMachine('"+item.uuid+"')\" height='24' title='Enable machine' style='cursor: pointer;'>";
                    }
                    handler_entry += "</td><td>";
                    if (item.test_mode) {
                        handler_entry += "<img src='../img/enabled_icon.png' onclick=\"disableTestModeMachine('"+item.uuid+"')\" height='24' title='Disable test mode' style='cursor: pointer;'>";
                    } else {
                        handler_entry += "<img src='../img/disabled_icon.png' onclick=\"enableTestModeMachine('"+item.uuid+"')\" height='24' title='Enable test mode' style='cursor: pointer;'>";
                    }
                    handler_entry += "<td>";                                        
                    handler_entry += "<img src='../img/cross.png' onclick=\"deleteMachine('"+item.uuid+"')\" height='24' title='Delete machine' style='cursor: pointer;'>";
                    handler_entry += "</td>";
                    handler_entry += "</tr>";
                    $("#MachineInfotable").append(handler_entry);
                }
                $("#MachineInfotable").append("</tbody>");
            }
        });
    });
}

function deleteMachine(machine_uuid) {
    confirmation_box_type=ConfirmationTypeEnum.DELETEMACHINE;
    confirmation_box_data={"machine_uuid" : machine_uuid};
    $("#dialog-confirm-text").text("Are you sure you want to delete this machine?");
    $( "#dialog-confirm" ).dialog("open");
}

function performMachineDelete() {    
    $.ajax({
        url: "/flask/machine/"+confirmation_box_data["machine_uuid"],
        type: "DELETE",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},        
        success: function(response) {
            getMachineInfo();
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Machine deletion failed");
        }
    });   
}

function enableTestModeMachine(machine_id) {
    $.ajax({
        url: "/flask/enabletestmodemachine/"+machine_id,
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},       
        success: function(response) {            
            getMachineInfo();
        },
        error: function(xhr) {
            //$("#userEditErrorMessage").removeClass().addClass("red self-center");
            //$("#userEditErrorMessage").html("<span>&#10007</span> User edit failed");
        }
    });
}

function disableTestModeMachine(machine_id) {
    $.ajax({
        url: "/flask/disabletestmodemachine/"+machine_id,
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},       
        success: function(response) {            
            getMachineInfo();
        },
        error: function(xhr) {
            //$("#userEditErrorMessage").removeClass().addClass("red self-center");
            //$("#userEditErrorMessage").html("<span>&#10007</span> User edit failed");
        }
    });
}

function enableMachine(machine_id) {
    $.ajax({
        url: "/flask/enablemachine/"+machine_id,
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},       
        success: function(response) {            
            getMachineInfo();
        },
        error: function(xhr) {
            //$("#userEditErrorMessage").removeClass().addClass("red self-center");
            //$("#userEditErrorMessage").html("<span>&#10007</span> User edit failed");
        }
    });
}

function disableMachine(machine_id) {
    $.ajax({
        url: "/flask/disablemachine/"+machine_id,
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},       
        success: function(response) {            
            getMachineInfo();
        },
        error: function(xhr) {
            //$("#userEditErrorMessage").removeClass().addClass("red self-center");
            //$("#userEditErrorMessage").html("<span>&#10007</span> User edit failed");
        }
    });
}

function showAddMachine() {
    $('#edit-machine-dialog-contents').load('templates/addmachine.html #addMachineScreen', function() {
        edit_machine_dialog.dialog( "open" );
    }); 
}

function performAddMachine() {
    var data = {};    
    data["machine_name"] = $('#machinename').val();
    data["host_name"] = $('#hostname').val();
    data["scheduler"] = $('#scheduler').val();
    data["connection_type"] = $('#connectionType').val();
    data["num_nodes"] = $('#number_nodes').val();
    data["cores_per_node"] = $('#number_cores').val();
    data["base_work_dir"] = $('#basedir').val();
    $.ajax({
        url: "/flask/addmachine",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(data),
        dataType: "json",
        success: function(response) {
            edit_machine_dialog.dialog( "close" );
            getMachineInfo();
        },
        error: function(xhr) {
            //$("#userEditErrorMessage").removeClass().addClass("red self-center");
            //$("#userEditErrorMessage").html("<span>&#10007</span> User edit failed");
        }
    });
}

function getEDIInfo() {
    checkAuthStillValid();
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/ediinfo.html", function() { 
        $.ajax({
            url: "/flask/getediinfo",
            type: "GET",
            headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},        
            success: function(response) {            
                var edi_handlers = response.handlers;
                $("#EDIInfotable").append("<tbody>");

                for (edi_handler in edi_handlers) {
                    var handler_entry = "<tr>";
                    item = edi_handlers[edi_handler];
                    handler_entry += "<td>"+item.endpoint + "</td>";                
                    if (item.pollperiod == null) {
                        handler_entry += "<td>PUSH</td>";
                    } else {
                        handler_entry += "<td>PULL ("+item.pollperiod+")</td>";
                    }
                    handler_entry += "<td>" + item.incidentid + "</td>";
                    handler_entry += "<td>" + item.queuename + "</td>";
                    
                    handler_entry += "<td><img src='../img/cross.png' class='click_button' width=26 height=26 onClick=\"deleteEDIHandler('"+item.queuename+"','"+item.endpoint+"','"+item.incidentid+"','"+item.pollperiod+"')\"></td>";
                    
                    handler_entry += "</tr>";

                    $("#EDIInfotable").append(handler_entry);
                }
                $("#EDIInfotable").append("</tbody>");
            },
            error: function(xhr) {
                console.log({"status": 500, "msg": "Internal system error, consult the logs for more details"});
            }
        });
    });
}

function deleteEDIHandler(queuename, endpoint, incidentid, pollperiod) {
    confirmation_box_type=ConfirmationTypeEnum.DELETEEDIHANDLER;
    confirmation_box_data={"queuename": queuename, "endpoint":endpoint, "incidentid": incidentid, "pollperiod" : pollperiod};
    $("#dialog-confirm-text").text("Are you sure you want to delete this handler?");
    $( "#dialog-confirm" ).dialog("open");
}

function getUsers() {
    checkAuthStillValid();
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/users.html", function() {
        $.ajax({
            url: "/flask/getallusers",
            type: "GET",
            headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
            success: function(response) {
                var users = JSON.parse(response.users);
                $("#userTable").append("<tbody>");

                for (item in users) {
                    var user_entry = "<tr>";
                    item = users[item];
                    user_entry += "<td>"+item.username+"   <i>(<span class=\"link\" onclick=\"manageUser('"+item.username+"');\">click here to edit</span>)</i></td>";
                    user_entry += "<td>" + item.name + "</td>";
                    user_entry += "<td>" + item.email + "</td>";
                    if (item.access_rights == 0) {
                        user_entry += "<td>user</td>";
                    } else if (item.access_rights == 1) {
                        user_entry += "<td>administrator</td>";
                    }
                    
                    if (item.enabled) {
                        user_entry += "<td>Yes</td>";
                    } else {
                        user_entry += "<td>No</td>";
                    }
                    
                    user_entry += "</tr>";

                    $("#userTable").append(user_entry);
                }
                $("#userTable").append("</tbody>");
            },
            error: function(xhr) {
                $("#confirmation").removeClass().addClass("button red self-center");
                $("#confirmation").html("<span>&#10007</span> User retrieval failed");
            }
        });
    });
}

function addWorkflowToUser() {
    var data = {};
    var username=$('#username').val();
    data["username"] = username;
    data["workflow"] = $('#all_registeredworkflows').val();
    $.ajax({
        url: "/flask/addusertoworkflow",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(data),
        dataType: "json",
        success: function(response) {            
            $("#registeredworkflows_users").append($('<option>', {value:data["workflow"], text: data["workflow"]}))
            $('#all_registeredworkflows').children('option[value="'+data["workflow"]+'"]').remove();
        },
        error: function(xhr) {
            $("#userEditErrorMessage").removeClass().addClass("red self-center");
            $("#userEditErrorMessage").html("<span>&#10007</span> Adding workflow to user failed");
        }
    });
}

function removeWorkflowFromUser() {    
    var data = {};
    var username=$('#username').val();
    data["username"] = username;
    data["workflow"] = $('#registeredworkflows_users').val();
    $.ajax({
        url: "/flask/removeuserfromworkflow",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(data),
        dataType: "json",
        success: function(response) {
            $('#registeredworkflows_users').children('option[value="'+data["workflow"]+'"]').remove();
            $("#all_registeredworkflows").append($('<option>', {value:data["workflow"], text: data["workflow"]}))
        },
        error: function(xhr) {
            $("#userEditErrorMessage").removeClass().addClass("red self-center");
            $("#userEditErrorMessage").html("<span>&#10007</span> Removing workflow from user failed");
        }
    });
}

function manageUser(username) {
    checkAuthStillValid();
    var wf = {};
    wf["username"] = username;
    var workflows;
    var users;
    $.when(
    $.ajax({
        url: "/flask/workflowinfo",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            workflows = JSON.parse(response.workflows);
        }
    }),
    $.ajax({
        url: "/flask/getuser",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            users = JSON.parse(response.users);            
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> User retrieval failed");
        }
    })
    ).then(function() {

        $('#edit-user-dialog-contents').load('templates/edituser.html #editUserScreen', function() {
            user=users[0]
            $('#username').val(user.username);
            $('#name').val(user.name);
            $('#email').val(user.email);
            if (user.access_rights == 0) {
                $('#type').val("user");
            } else if (user.access_rights == 1) {
                $('#type').val("administrator");
            }
            $('#enabled').prop('checked', user.enabled);
            $("#registeredworkflows_users").empty();
            var usersWorkflows = []
            for (wf in user.workflows) {
                wf=user.workflows[wf];
                usersWorkflows.push(wf);
                $("#registeredworkflows_users").append($('<option>', {value:wf, text: wf}))
            }
            $("#all_registeredworkflows").empty();
            for (wf in workflows) {
                wf=workflows[wf].kind;
                if (!usersWorkflows.includes(wf)) {
                    $("#all_registeredworkflows").append("<option value='"+wf+"'>"+wf+"</option>");
                }
            }
            edit_user_dialog.dialog( "open" );
        }); 
    });
}

function deleteUser() {
    confirmation_box_type=ConfirmationTypeEnum.DELETEUSER;    
    $("#dialog-confirm-text").text("Are you sure you want to delete this user?");
    $( "#dialog-confirm" ).dialog("open");
}

function performUserDeletion() {
    var wf = {};
    wf["username"] = $("#username").val();
    $.ajax({
        url: "/flask/deleteuser",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            edit_user_dialog.dialog( "close" );
            getUsers();
        },
        error: function(xhr) {
            $("#userEditErrorMessage").removeClass().addClass("red self-center");
            $("#userEditErrorMessage").html("<span>&#10007</span> Deletion of user failed");
        }
    });
}

function changePassword() {
    var wf = {};
    wf["username"] = $("#username").val();
    wf["password"] = $("#password").val();
    $.ajax({
        url: "/flask/changepassword",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            edit_user_dialog.dialog( "close" );
            getUsers();
        },
        error: function(xhr) {
            $("#userEditErrorMessage").removeClass().addClass("red self-center");
            $("#userEditErrorMessage").html("<span>&#10007</span> Changing user password failed");
        }
    });
}

function editUser() {
    var wf = {};
    wf["username"] = $("#username").val();
    wf["name"] = $("#name").val();
    wf["email"] = $("#email").val();
    wf["type"] = $("#type").val();
    wf["enabled"] = $("#enabled").prop('checked');
    $.ajax({
        url: "/flask/edituser",
        type: "POST",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        contentType: "application/json",
        data: JSON.stringify(wf),
        dataType: "json",
        success: function(response) {
            edit_user_dialog.dialog( "close" );
            getUsers();
        },
        error: function(xhr) {
            $("#userEditErrorMessage").removeClass().addClass("red self-center");
            $("#userEditErrorMessage").html("<span>&#10007</span> User edit failed");
        }
    });
}

function getSystemHealth() {
    checkAuthStillValid();
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/health.html", function() {
    $.ajax({
        url: "/flask/health",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            var health = JSON.parse(response.health);
            $("#healthTable").append("<tbody>");

            for (item in health) {
                var health_entry = "<tr>";
                item = health[item];
                health_entry += "<td>" + item.name + "</td>";
                if (item.status == true) {
                    health_entry += "<td><img src='../img/tick.png' width=32 height=32></td>";
                } else {
                    health_entry += "<td><img src='../img/cross.png' width=32 height=32></td>";
                }
                health_entry += "</tr>";

                $("#healthTable").append(health_entry);
            }
            $("#healthTable").append("</tbody>");
        },
        error: function(xhr) {
            $("#confirmation").removeClass().addClass("button red self-center");
            $("#confirmation").html("<span>&#10007</span> Health check failed");
        }
    });
    });
}

function getLogs() {
    checkAuthStillValid();
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").removeClass("blue");
    $("#body-container").load("../templates/logs.html", function() {

    $.ajax({
        url: "/flask/logs",
        type: "GET",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            var logs = JSON.parse(response.logs);
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

function logOut() {
    $("#nav-home").removeClass("blue");
    $("#nav-dash").removeClass("blue");
    $("#nav-logout").addClass("blue");

    $.ajax({
        url: "/flask/logout",
        type: "DELETE",
        headers: {'Authorization': 'Bearer ' + sessionStorage.getItem("access_token")},
        success: function(response) {
            if (response.status == 200) {
                sessionStorage.removeItem("access_token");
                window.location.href = "/login";
            }
        }
    });
}

