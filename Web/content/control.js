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
	                      + $("#sh").val() + '/' + $("#co").val() + '/' + $("#sa").val()
		,'Snapshot Image');
    return false;
});

$( "#btn_refresh" ).click(function() {
    $("#status_id").html("Refreshing ...");	
    $.post("/api/refresh", {
			   "ss": $( "#ss" ).val(), "iso": $("#iso").val(), "br": $("#br").val(),
			   "sh": $( "#sh" ).val(), "co": $("#co").val(), "sa": $("#sa").val() 
			   }, function(msg) {
    })
    .done(function(msg) {
        if( v_updimage != null )
	    clearTimeout(v_updimage);

	var canvas = $('#canvas')[0];
        var context = canvas.getContext('2d');
        //context.restore();

        var img = new Image();
	img.src = "data:image/jpeg;base64," + msg['image'];
        img.onload = function() {
            $("#status_id").html("Refreshed");	
            context.drawImage(this, 0, 0);
            if( $.cookie("norefresh") != "true" )
                v_updimage = setTimeout(updateImage, 1000); // 1 * 1000 miliseconds
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
    $.post("/api/motor/v/forward", {"speed": $( "#vspeed" ).val(), "steps": $("#vsteps").val()}, function(data) {
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
    $.post("/api/motor/v/backward", {"speed": $( "#vspeed" ).val(), "steps": $("#vsteps").val()}, function(data) {
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
    $.post("/api/motor/h/forward", {"speed": $( "#hspeed" ).val(), "steps": $("#hsteps").val()}, function(data) {
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
    $.post("/api/motor/h/backward", {"speed": $( "#hspeed" ).val(), "steps": $("#hsteps").val()}, function(data) {
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
	    $("#ss").val('1000');
	    $("#iso").val('800');
        }
});

$('input[type=checkbox][name=refined]').click( function(){
    if( $(this).is(':checked') ) 
	$.cookie("refined", "true");
    else
	$.cookie("refined", "false");
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
            var client = new WebSocket( 'ws://jupiter8.dyndns.org:8084/' );
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
		"vsteps": $("#vsteps").val(),
		"hspeed": $( "#hspeed" ).val(), 
		"hsteps": $("#hsteps").val()
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
    $.post("/api/motor/f/forward", {"steps": $("#focus_step").val()}, function(data) {
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
    $.post("/api/motor/f/backward", {"steps": $("#focus_step").val()}, function(data) {
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

