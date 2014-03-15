jQuery(document).ready(function() {
    var foo = jQuery('#time_id');
  
    function updateTime() {
        //var now = new Date();

	$.getJSON( "/api/gettime", function( data ) {
  	    $.each( data, function( key, val ) {
              foo.html(val); 
  	    });
	});
    }
  
    updateTime();
    setInterval(updateTime, 5000); // 5 * 1000 miliseconds
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
