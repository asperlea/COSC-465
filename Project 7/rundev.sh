#!/bin/bash

if [[ -n `which node` ]]; then
    export NODE=`which node`
elif [[ -n `which nodejs` ]]; then
    export NODE=`which nodejs`
else
    echo "No node.js executable found (looked for both node and nodejs)"
    exit
fi

NODE_ENV=development BASE_URL=http://localhost:3000 $NODE app.js

