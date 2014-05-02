exports.ping = function(req) {
    // req is https://github.com/techpines/express.io/tree/master/lib#socketrequest
    console.log("Got ping socket.io callback");
    req.io.emit('pong' + req.data.ping_id, req.data);
    //uniquely identify which listener the message is meant for
};

exports.file = function(req) {
    console.log("Received file");
    req.io.emit('received' + req.data.file_id, req.data);
};


