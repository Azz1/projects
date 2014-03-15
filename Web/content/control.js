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
  
    updateTime();
    setInterval(updateTime, 5000); // 5 * 1000 miliseconds
});

$( "#btn_refresh" ).click(function() {
    $.post("/api/refresh", {}, function(msg) {
    })
    .done(function(msg) {
	var canvas = $('#canvas')[0];
        var context = canvas.getContext('2d');

        var img = new Image();
	img.src = "data:image/jpeg;base64," + msg['image'];
        context.drawImage(img, 0, 0);
    })
    .fail(function() {
      alert( "camera controll error!" );
    })
    .always(function() {
  });
});

$( "#btn_up" ).click(function() {
    $.post("/api/motor/v/forward", {"speed": $( "#vspeed" ).val(), "steps": $("#vsteps").val()}, function(data) {
    })
    .done(function() {
    })
    .fail(function() {
      alert( "motor controll error!" );
    })
    .always(function() {
  });
});

$( "#btn_down" ).click(function() {
    $.post("/api/motor/v/backward", {"speed": $( "#vspeed" ).val(), "steps": $("#vsteps").val()}, function(data) {
    })
    .done(function() {
    })
    .fail(function() {
      alert( "motor controll error!" );
    })
    .always(function() {
  });
});

$( "#btn_left" ).click(function() {
    $.post("/api/motor/h/forward", {"speed": $( "#hspeed" ).val(), "steps": $("#hsteps").val()}, function(data) {
    })
    .done(function() {
    })
    .fail(function() {
      alert( "motor controll error!" );
    })
    .always(function() {
  });
});

$( "#btn_right" ).click(function() {
    $.post("/api/motor/h/backward", {"speed": $( "#hspeed" ).val(), "steps": $("#hsteps").val()}, function(data) {
    })
    .done(function() {
    })
    .fail(function() {
      alert( "motor controll error!" );
    })
    .always(function() {
  });
});
