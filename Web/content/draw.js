$(function() {
    var drawLine = false;

    var theCanvas = document.getElementById('canvas');
    var finalPos = {x:0, y:0};
    var startPos = {x:0, y:0};
    var ctx = theCanvas.getContext('2d');

    // create backing canvas
    var backCanvas = document.getElementById('bkcanvas');
    var backCtx = backCanvas.getContext('2d');

    var canvasOffset = $('#canvas').offset();

    function line(cnvs) {
        cnvs.beginPath();
        cnvs.moveTo(2*startPos.x-finalPos.x, 2*startPos.y-finalPos.y);
        cnvs.lineTo(finalPos.x, finalPos.y);
        cnvs.stroke();
        cnvs.beginPath();
        cnvs.arc(startPos.x, startPos.y, 3, 0, 2 * Math.PI, false);
        cnvs.stroke();
    }

    function clearCanvas()
    {
       //ctx.clearRect(0, 0, theCanvas.width, theCanvas.height);
       ctx.drawImage(backCanvas, 0,0);
    }

    $('#canvas').mousemove(function(e) {
        if (drawLine === true) {
            finalPos = {x: e.pageX - canvasOffset.left, y:e.pageY - canvasOffset.top};

            clearCanvas();
            line(ctx);
            
        }
    });

    $('#canvas').mousedown(function(e) {
        switch (event.which) {
        case 1:	//Left click
            drawLine = true;
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 1;
            ctx.lineCap = 'round';
            ctx.beginPath();
            startPos = { x: e.pageX - canvasOffset.left, y: e.pageY - canvasOffset.top};
	    break;
        case 3:	//Right click
            drawLine = false;
	    break;
        }
    });

    $('#canvas').mouseup(function() {
        switch (event.which) {
        case 1:	//Left click
            clearCanvas();
            // Replace with var that is second canvas
            line(ctx);
	    $('#refsel').val(startPos.x.toString() + "," + startPos.y.toString() + "," + finalPos.x.toString() + "," + finalPos.y.toString());
            //finalPos = {x:0, y:0};
            //startPos = {x:0, y:0};
            drawLine = false;
	    break;
        case 3:	//Right click
	    break;
        }
    });
});
