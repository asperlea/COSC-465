import urllib2
import socket
import sys

if len(sys.argv) != 3:
    print >>sys.stderr,"Usage: {} host(h1,h2,h3) filename".format(sys.argv[0])
    sys.exit()

host = sys.argv[1]
if host not in ['h2','h3','h4']:
    print >>sys.stderr,"Host name must be h2, h3, or h4"
    sys.exit()

filename = sys.argv[2]
try:
    urlhandle = urllib2.urlopen("http://10.0.0.{}/{}".format(host[1],filename))
    contents = urlhandle.read()
    urlhandle.close()
    print "Retrieved: <{}>".format(contents)
except urllib2.HTTPError as e:
    print "Request failed: ",str(e)
except socket.error as e:
    print "Low-level transport error:",str(e)

