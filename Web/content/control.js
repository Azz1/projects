var v_updimage;

function updateImage() {
    $( "#btn_refresh" ).click();
}

jQuery(document).ready(function() {
    var foo = jQuery('#time_id');
  
    function updateTime() {
        //var now = new Date();

	$.getJSON( "/api/gettime/" + $("#tgazadj").val() + '/' + $("#tgaltadj").val(), function( data ) {
  	    $.each( data, function( key, val ) {
	      if( key == "time" )
              	foo.html(val); 
	      if( key == "tgaz" )
		$("#tgaz_l").html(val); 
	      if( key == "tgalt" )
		$("#tgalt_l").html(val); 
	      if( key == "curaz" )
		$("#curaz").html(val); 
	      if( key == "curalt" )
		$("#curalt").html(val); 
  	    });
	});
        //$( "#btn_refresh" ).click();
    }
  
    $.getJSON( "/api/init", function( data ) {
  	    $.each( data, function( key, val ) {
              $("#"+ key ).val(val); 
  	    });
    	    updateImage();
	});

    if( $.cookie("refined") == "true" )
        $('input[type=checkbox][name=refined]').prop("checked", true);
    else
        $('input[type=checkbox][name=refined]').prop("checked", false);

    if( $.cookie("rawmode") == "true" )
        $('input[type=checkbox][name=rawmode]').prop("checked", true);
    else
        $('input[type=checkbox][name=rawmode]').prop("checked", false);

    if( $.cookie("vflip") == "true" )
        $('input[type=checkbox][name=vflip]').prop("checked", true);
    else
        $('input[type=checkbox][name=vflip]').prop("checked", false);

    if( $.cookie("hflip") == "true" )
        $('input[type=checkbox][name=hflip]').prop("checked", true);
    else
        $('input[type=checkbox][name=hflip]').prop("checked", false);

    if( $.cookie("cmode") == "night" ) {
        $('input[type=radio][name=cmode]')[0].checked = false;
        $('input[type=radio][name=cmode]')[1].checked = true;
    } else {
        $('input[type=radio][name=cmode]')[0].checked = true;
        $('input[type=radio][name=cmode]')[1].checked = false;
    }

    $('input[type=radio][name=cmode]').change();

    updateTime();
    setInterval(updateTime, 5000); // 2 * 1000 miliseconds
});

$( "#btn_videoshot" ).click(function() {
    $("#status_id").html("Refreshing ...");	

    var urls = "/api/videoshot/" + $("#ss").val() + '/' + $("#iso").val() + '/' + $("#br").val() + '/'
	                      + $("#sh").val() + '/' + $("#co").val() + '/' + $("#sa").val() + '/'
			      + $("#videolen").val();

    window.location.href = urls;
    return false;
});

$( "#btn_snapshot" ).click(function() {
    popImage('/api/snapshot/' + $("#ss").val() + '/' + $("#iso").val() + '/' + $("#br").val() + '/'
	                      + $("#sh").val() + '/' + $("#co").val() + '/' + $("#sa").val() + '/'
			      + $("#timelapse").val()
		,'Snapshot Image');
    return false;
});

$( "#btn_refresh" ).click(function() {
    $("#status_id").html("Refreshing ...");	
    $.post("/api/refresh", {
			   "ss": $( "#ss" ).val(), "iso": $("#iso").val(), "br": $("#br").val(),
			   "sh": $( "#sh" ).val(), "co": $("#co").val(), "sa": $("#sa").val(), 
                           "cmode": ($('input[type=radio][name=cmode]')[1].checked ? 'night' : 'day'), 
                           "rawmode": ($('input[type=checkbox][name=rawmode]').is(':checked')? 'true':'false'),
                           "vflip": ($('input[type=checkbox][name=vflip]').is(':checked')? 'true':'false'),
                           "hflip": ($('input[type=checkbox][name=hflip]').is(':checked')? 'true':'false'),
		           "refpoints": $('#refsel').val(),
                           "tk_blur_limit": (typeof trackingwin === 'undefined')? '' : $('#blurlimit', trackingwin.document).val(),
                           "tk_thresh_limit": (typeof trackingwin === 'undefined')? '' : $('#thresh', trackingwin.document).val()
			   }, function(msg) {
    })
    .done(function(msg) {
        if( v_updimage != null )
	    clearTimeout(v_updimage);

	var canvas = $('#canvas')[0];
        var context = canvas.getContext('2d');
	var bkcanvas = $('#bkcanvas')[0];
        var contextb = bkcanvas.getContext('2d');
        //context.restore();

        var img = new Image();
	img.src = "data:image/jpeg;base64," + msg['image'];
        img.onload = function() {
            $("#status_id").html("Refreshed");	
            context.drawImage(this, 0, 0);
        
            // save main canvas contents
            contextb.drawImage(this, 0,0);

            if( $.cookie("norefresh") != "true" )
                v_updimage = setTimeout(updateImage, 1000); // 1 * 1000 miliseconds
        }

        if(typeof trackingwin !== 'undefined') {	// Update Tracking window
	    if( msg['trackinghistory'].length > 0) {
		var str = "";
		for (var i = msg['trackinghistory'].length - 1; i >= 0; i--) {
		   str += msg['trackinghistory'][i].timestamp + ":<br/> dRA=" + msg['trackinghistory'][i].d_ra + ", dDec=" + msg['trackinghistory'][i].d_dec + "<br/><br/>";
	 	}
		$('#log', trackingwin.document).html(str);
	    }
	    drawgrid(msg['trackinghistory']);
	}
    })
    .fail(function() {
      $("#status_id").html("camera control error!" );
      if( $.cookie("norefresh") != "true" )
          v_updimage = setTimeout(updateImage, 5000); // 5 * 1000 miliseconds
    })
    .always(function() {
    });
    return false;
});

$( "#btn_up" ).click(function() {
    $.post("/api/motor/v/forward", {"speed": $( "#vspeed" ).val(), "adj": 0, "steps": $("#vsteps").val()}, function(data) {
    })
    .done(function(data) {
	if( data["detai"] != "")
	    $("#status_id").html(data["detail"]);	
    })
    .fail(function() {
      $("#status_id").html("motor control error!" );
    })
    .always(function() {
    });
    return false;
});

$( "#btn_down" ).click(function() {
    $.post("/api/motor/v/backward", {"speed": $( "#vspeed" ).val(),  "adj": 0, "steps": $("#vsteps").val()}, function(data) {
    })
    .done(function(data) {
	if( data["detai"] != "")
	    $("#status_id").html(data["detail"]);	
    })
    .fail(function() {
      $("#status_id").html("motor control error!" );
    })
    .always(function() {
    });
    return false;
});

$( "#btn_left" ).click(function() {
    $.post("/api/motor/h/forward", {"speed": $( "#hspeed" ).val(),  "adj": $( "#hadj" ).val(), "steps": $("#hsteps").val()}, function(data) {
    })
    .done(function(data) {
	if( data["detai"] != "")
	    $("#status_id").html(data["detail"]);	
    })
    .fail(function() {
      $("#status_id").html("motor control error!" );
    })
    .always(function() {
    });
    return false;
});

$( "#btn_right" ).click(function() {
    $.post("/api/motor/h/backward", {"speed": $( "#hspeed" ).val(),  "adj": $( "#hadj" ).val(), "steps": $("#hsteps").val()}, function(data) {
    })
    .done(function(data) {
	if( data["detai"] != "")
	    $("#status_id").html(data["detail"]);	
    })
    .fail(function() {
      $("#status_id").html("motor control error!" );
    })
    .always(function() {
    });
    return false;
});

$('input[type=radio][name=cmode]').change(function() {
        if (this.value == 'day') {
	    $.cookie("cmode", "day");
	    $("#ss").val('1');
	    $("#iso").val('400');
        }
        else {
	    $.cookie("cmode", "night");
	    $("#ss").val('800');
	    $("#iso").val('1600');
        }
});

$('input[type=checkbox][name=refined]').click( function(){
    if( $(this).is(':checked') ) 
	$.cookie("refined", "true");
    else
	$.cookie("refined", "false");
});

$('input[type=checkbox][name=rawmode]').click( function(){
    if( $(this).is(':checked') ) 
	$.cookie("rawmode", "true");
    else
	$.cookie("rawmode", "false");
});

$('input[type=checkbox][name=vflip]').click( function(){
    if( $(this).is(':checked') ) 
	$.cookie("vflip", "true");
    else
	$.cookie("vflip", "false");
});

$('input[type=checkbox][name=hflip]').click( function(){
    if( $(this).is(':checked') ) 
	$.cookie("hflip", "true");
    else
	$.cookie("hflip", "false");
});

$('input[type=checkbox][name=norefresh]').click( function(){
    if( $(this).is(':checked') ) {
	$.cookie("norefresh", "true");

        var urls = "/api/startvideo/" + $("#ss").val() + '/' + $("#iso").val() + '/' + $("#br").val() + '/'
	                      + $("#sh").val() + '/' + $("#co").val() + '/' + $("#sa").val();

	$.getJSON( urls, function( data ) {
            $("#status_id").html("video started!" );

            // Show loading notice
            //var canvas = $('#canvas')[0];
            var canvas = document.getElementById('canvas');
            var context = canvas.getContext('2d');
            //context.restore();
	    //context.scale(2.1875, 2.1875);
    
            // Setup the WebSocket connection and start the player
            var client = new WebSocket( 'ws://[IPADDRESS]:8084/' );
            var player = new jsmpeg(client, {canvas:canvas});

	});

    } else {
	$.cookie("norefresh", "false");

	$.getJSON( "/api/stopvideo", function( data ) {
            $("#status_id").html("video stopped!" );

            var canvas = document.getElementById('canvas');
            var context = canvas.getContext('2d');
	    context.canvas.width = 700;
	    context.canvas.height = 525;
  	});

    }

});

$('input[type=checkbox][name=tracking]').click( function(){
    if( $(this).is(':checked') ) {
	$.cookie("tracking", "true");

        if(typeof trackingwin === 'undefined' || trackingwin.closed) 
            trackingwin = window.open(window.location.href.substring(0,window.location.href.lastIndexOf("/")+1)+"tracking.html",
                    "_blank",
                    "titlebar=no,location=no,menubar=no,toobar=no,top=400,left=600,width=600,height=160");

        $.post("/api/starttracking", {
		"myloclat": $( "#myloclat" ).val(), 
		"myloclong": $("#myloclong").val(), 
		"altazradec": $('input[type=radio][name=altazradec]')[0].checked? 'ALTAZ' : 'RADEC', 
		"tgaz": $("#tgaz").val(), 
		"tgalt": $("#tgalt").val(), 
		"tgazadj": $("#tgazadj").val(), 
		"tgaltadj": $("#tgaltadj").val(), 
		"tgrah": $("#tgrah").val(), 
		"tgram": $("#tgram").val(), 
		"tgras": $("#tgras").val(), 
		"tgdecdg": $("#tgdecdg").val(), 
		"tgdecm": $("#tgdecm").val(), 
		"tgdecs": $("#tgdecs").val(),
		"vspeed": $( "#vspeed" ).val(), 
		"vadj": 0, 
		"vsteps": $("#vsteps").val(),
		"hspeed": $( "#hspeed" ).val(), 
		"hadj": $( "#hadj" ).val(), 
		"hsteps": $("#hsteps").val(),
		"refpoints": $('#refsel').val()
		}, function(data) {
        })
        .done(function(data) {
	    if( data["detai"] != "")
            	$("#status_id").html(data["detail"]);
	    else
                $("#status_id").html("tracking started!" );
        })
        .fail(function() {
          $("#status_id").html("start tracking failed!" );
        })
        .always(function() {
        });
    } else {
	$.cookie("tracking", "false");
        //trackingwin.close(); 

	$.getJSON( "/api/stoptracking", function( data ) {
            $("#status_id").html("tracking stopped!" );
  	});

    }

});

$( "#adjoffset" ).click(function() {
  $.post("/api/adjoffset", {}, function(data) {
    })
    .done(function(data) {
        if( data["detai"] != "")
            $("#tgazadj").val(data["azadj"]);
            $("#tgaltadj").val(data["altadj"]);
    })
    .fail(function() {
      $("#status_id").html("offset adjustment error!" );
    })
    .always(function() {
    });

  return false;
});

$( "#focus_in" ).click(function() {
    $.post("/api/motor/f/forward", {"speed": 5,  "adj": 0, "steps": $("#fsteps").val()}, function(data) {
    })
    .done(function(data) {
        if( data["detai"] != "")
            $("#status_id").html(data["detail"]);
    })
    .fail(function() {
      $("#status_id").html("motor control error!" );
    })
    .always(function() {
    });
    return false;
});

$( "#focus_out" ).click(function() {
    $.post("/api/motor/f/backward", {"speed": 5,  "adj": 0, "steps": $("#fsteps").val()}, function(data) {
    })
    .done(function(data) {
        if( data["detai"] != "")
            $("#status_id").html(data["detail"]);
    })
    .fail(function() {
      $("#status_id").html("motor control error!" );
    })
    .always(function() {
    });
    return false;
});


$( "#halt" ).click(function() {
  $.post("/api/halt", {}, function(data) {
    })
    .done(function(data) {
    })
    .fail(function() {
      $("#status_id").html("Invalid operation, no permission!" );
    })
    .always(function() {
    });

  return false;
});

function drawgrid(points) {
    var grid_size = 300/20;
    var x_axis_distance_grid_lines = 3;
    var y_axis_distance_grid_lines = 2;
    var x_axis_starting_point = { number: 1, suffix: '' };
    var y_axis_starting_point = { number: 1, suffix: '' };

    var canvas = trackingwin.document.getElementById("canvastr"); 
    var ctx = canvas.getContext("2d");
    
    // canvas width
    var canvas_width = canvas.width;

    // canvas height
    var canvas_height = canvas.height;
    ctx.clearRect(0, 0, canvas_width, canvas_height);

    // no of vertical grid lines
    var num_lines_x = Math.floor(canvas_height/grid_size);

    // no of horizontal grid lines
    var num_lines_y = Math.floor(canvas_width/grid_size);

    // Draw grid lines along X-axis
    for(var i=0; i<=num_lines_x; i++) {
        ctx.beginPath();
        ctx.lineWidth = 1;
    
        // If line represents X-axis draw in different color
        if(i == x_axis_distance_grid_lines) 
            ctx.strokeStyle = "#e9e919";
        else
            ctx.strokeStyle = "#151515";
    
        if(i == num_lines_x) {
            ctx.moveTo(0, grid_size*i);
            ctx.lineTo(canvas_width, grid_size*i);
        }
        else {
            ctx.moveTo(0, grid_size*i+0.5);
            ctx.lineTo(canvas_width, grid_size*i+0.5);
        }
        ctx.stroke();
    }

    // Draw grid lines along Y-axis
    for(i=0; i<=num_lines_y; i++) {
        ctx.beginPath();
        ctx.lineWidth = 1;
    
        // If line represents Y-axis draw in different color
        if(i == y_axis_distance_grid_lines) 
            ctx.strokeStyle = "#e9e919";
        else
            ctx.strokeStyle = "#151515";
    
        if(i == num_lines_y) {
            ctx.moveTo(grid_size*i, 0);
            ctx.lineTo(grid_size*i, canvas_height);
        }
        else {
            ctx.moveTo(grid_size*i+0.5, 0);
            ctx.lineTo(grid_size*i+0.5, canvas_height);
        }
        ctx.stroke();
    }

    ctx.save();
    ctx.translate(y_axis_distance_grid_lines*grid_size, x_axis_distance_grid_lines*grid_size);

    // Ticks marks along the positive X-axis
    for(i=1; i<(num_lines_y - y_axis_distance_grid_lines); i++) {
        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = "#595919";

        // Draw a tick mark 6px long (-3 to 3)
        ctx.moveTo(grid_size*i+0.5, -3);
        ctx.lineTo(grid_size*i+0.5, 3);
        ctx.stroke();

        // Text value at that point
        //ctx.font = '9px Arial';
	//ctx.fillStyle = "#595919";
        //ctx.textAlign = 'start';
        //ctx.fillText(x_axis_starting_point.number*i + x_axis_starting_point.suffix, grid_size*i-2, 15, 100);
    }

    // Ticks marks along the positive Y-axis
    // Positive Y-axis of graph is negative Y-axis of the canvas
    for(i=1; i<(num_lines_x - x_axis_distance_grid_lines); i++) {
        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = "#595919";

        // Draw a tick mark 6px long (-3 to 3)
        ctx.moveTo(-3, grid_size*i+0.5);
        ctx.lineTo(3, grid_size*i+0.5);
        ctx.stroke();

        // Text value at that point
        ctx.font = '9px Arial';
	ctx.fillStyle = "#595919";
        ctx.textAlign = 'end';
        ctx.fillText(-y_axis_starting_point.number*i*grid_size + y_axis_starting_point.suffix, -8, grid_size*i+3, 100);
    }

    // Ticks marks along the negative Y-axis
    // Negative Y-axis of graph is positive Y-axis of the canvas
    for(i=1; i<x_axis_distance_grid_lines; i++) {
        ctx.beginPath();
        ctx.lineWidth = 1;
        ctx.strokeStyle = "#595919";

        // Draw a tick mark 6px long (-3 to 3)
        ctx.moveTo(-3, -grid_size*i+0.5);
        ctx.lineTo(3, -grid_size*i+0.5);
        ctx.stroke();

        // Text value at that point
        ctx.font = '9px Arial';
	ctx.fillStyle = "#595919";
        ctx.textAlign = 'end';
        ctx.fillText(y_axis_starting_point.number*i*grid_size + y_axis_starting_point.suffix, -8, -grid_size*i+3, 100);
    }

    // Draw lines based on data
    // Draw Delta-RA line
    ctx.beginPath();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#a97919";
    for( i in points ) {
	var d_ra = points[i].d_ra;
	if(d_ra >= canvas_height/2) d_ra = canvas_height/2-1;
	if(d_ra <= -canvas_height/2) d_ra = -canvas_height/2+1;
	if( i== 0 )
	  ctx.moveTo(i*grid_size, -1*d_ra);
	else
	  ctx.lineTo(i*grid_size, -1*d_ra);
    }
    ctx.stroke();

    // Draw Delta-DEC line
    ctx.beginPath();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#39e9e9";
    for( i in points ) {
	var d_dec = points[i].d_dec;
	if(d_dec >= canvas_height/2) d_dec = canvas_height/2-1;
	if(d_dec <= -canvas_height/2) d_dec = -canvas_height/2+1;
	if( i== 0 )
	  ctx.moveTo(i*grid_size, -1*d_dec);
	else
	  ctx.lineTo(i*grid_size, -1*d_dec);
    }
    ctx.stroke();

    ctx.restore();
}

