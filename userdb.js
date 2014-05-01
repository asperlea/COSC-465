var userhash = { };  //session ID -> user data
var next_anonymous = 1; 

var add_user = function(id, user) {
    if (userhash[id] === undefined) {
        if (!user) {
            user = "anonymous" + next_anonymous;
            next_anonymous += 1;
        }
        userhash[id] = {
            'id': id,
            'user': user,
            'latency_results': []
        };
    }
    return userhash[id];
};

var logresults = function(req) {
	var id = req.session.id;
	var avg = req.data.avg;
	
	add_user(id, undefined); //be sure they're in there
	userhash[id].latency_results = avg;
	console.log("Logged avg of " + avg + " for " + userhash[id].user + "'s test");
};

exports.logresults = logresults;
exports.add_user = add_user;
exports.get_user_name = function(id) {
    if (userhash[id] === undefined) {
        add_user(id, undefined);
    }
    return userhash[id].user;
};