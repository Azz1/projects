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

