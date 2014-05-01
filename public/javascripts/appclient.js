var myapp = (function(){
	var start_ping = function() {
		var socket = io.connect();  
		socket.emit('ping', {timestamp: Date.now()});
		socket.on('pong', function(data) {
		    var rtt = Date.now() - data.timestamp;
		    console.log("Ping RTT (milliseconds): " + rtt);
		});
	};
	
    return {
        init: function() {
            console.log("Client-side app starting up");
			jQuery("#startping").click(start_ping);
        }
    }
})();
jQuery(myapp.init);

