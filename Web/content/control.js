var v_updimage;

function updateImage() {
    $( "#btn_refresh" ).click();
}

jQuery(document).ready(function() {
    var foo = jQuery('#time_id');
  
    function updateTime() {
        //var now = new Date();

	$.getJSON( "/api/gettime", function( data ) {
  	    $.each( data, function( key, val ) {
              foo.html(val); 
  	    });
	});
        //$( "#btn_refresh" ).click();
    }
  
    $.getJSON( "/api/init", function( data ) {
  	    $.each( data, function( key, val ) {
              $("#"+ key ).val(val); 
  	    });
	});

    updateTime();
    setInterval(updateTime, 5000); // 5 * 1000 miliseconds
    updateImage();
});

$( "#btn_snapshot" ).click(function() {
    popImage('/api/snapshot/' + $("#ss").val() + '/' + $("#iso").val() + '/' + $("#br").val() + '/'
	                      + $("#sh").val() + '/' + $("#co").val() + '/' + $("#sa").val()
		,'Snapshot Image');
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

        var img = new Image();
	img.src = "data:image/jpeg;base64," + msg['image'];
        img.onload = function() {
            $("#status_id").html("Refreshed");	
            context.drawImage(this, 0, 0);
            v_updimage = setTimeout(updateImage, 2000); // 2 * 1000 miliseconds
        }

    })
    .fail(function() {
      $("#status_id").html("camera control error!" );
    })
    .always(function() {
  });
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
});

$('input[type=radio][name=cmode]').change(function() {
        if (this.value == 'day') {
	    $("#ss").val('1');
	    $("#iso").val('400');
        }
        else {
	    $("#ss").val('1000');
	    $("#iso").val('400');
        }
});
