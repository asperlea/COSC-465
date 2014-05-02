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

	var start_throughput = function() {
		var throughput;
		var fake_file = new Float64Array(12800); // size of this is 12800 * 8 bytes per float
		var socket = io.connect();
		
		var my_id = listener_id; // uniquely id start_throughput funcs

		socket.emit('file', {timestamp: Date.now(), file_id: my_id, content: fake_file});
		console.log("Got here");
		socket.on('received' + my_id, function(data) {
			var rtt = Date.now() - data.timestamp;
			throughput = 12800 * 8 * 2 / rtt; // rtt is in ms so to get bytes/second 
			throughput = throughput / 1000;

			socket.emit('logthroughput', {throughput: throughput}); // send off test results to database

			jQuery("#throughput_results").text("Test average: " + throughput + " bytes/second.");
		});
	};
	
    return {
        init: function() {
            console.log("Client-side app starting up");
	    jQuery("#startping").click(start_ping);
	    jQuery("#startthroughput").click(start_throughput);
        }
    }
})();
jQuery(myapp.init);

