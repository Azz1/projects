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
		           "refpoints": $('#refsel').val()
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

	    // nodejs 8 + jsmpg
            //var client = new WebSocket( 'ws://[IPADDRESS]:8084/' );
            //var player = new jsmpeg(client, {canvas:canvas}); 

	    // nodejs 10 + JSMpeg
            var url = 'ws://[IPADDRESS]:8084/';
            var player = new JSMpeg.Player(url, {canvas:canvas, audio:false, disableGl:true});

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

