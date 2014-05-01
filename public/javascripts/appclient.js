var listener_id = 10;

var myapp = (function(){
	var start_ping = function() {
		var rtt_list = [];
		var socket = io.connect();
		
		var my_id = listener_id; //uniquely id start_ping funcs
		listener_id += 1;
		
		socket.emit('ping', {timestamp: Date.now(), ping_id: my_id});
		socket.on('pong' + my_id, function(data) {
			if (rtt_list.length < 5) {
				var rtt = Date.now() - data.timestamp;
				//console.log("Ping RTT (milliseconds): " + rtt);
				rtt_list.push(rtt);
				socket.emit('ping', {timestamp: Date.now(), ping_id: my_id});
			}else{
				//Reached end of our work here, we'll never get to this func again
				console.log("RTT List: " + rtt_list);
				var sum = rtt_list.reduce(function(prevVal, curVal){
					return curVal + prevVal;
				});
				var avg = sum / 5.0;
				console.log("Avg: " + avg);
				
				socket.emit('logresults', {avg: avg}); //send off test results to database
				
				jQuery("#ping_results").text("Test average: " + avg + "ms.");
			}
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

