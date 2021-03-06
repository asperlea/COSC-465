#!/usr/bin/env python

__author__ = "asperlea@colgate.edu, cwmahoney@colgate.edu"
__doc__ = '''
A simple model-view controller-based message board/chat client application.
-Now including stop-and-wait and a checksum implementation
2/9/2014
'''

import sys
import Tkinter
import socket
from select import select
import argparse


class MessageBoardNetwork(object):
	'''
	Model class in the MVC pattern.  This class handles
	the low-level network interactions with the server.
	It should make GET requests and POST requests (via the
	respective methods, below) and return the message or
	response data back to the MessageBoardController class.
	'''
	def __init__(self, host, port, retries, timeout):
		'''
		Constructor.  You should create a new socket
		here and do any other initialization.
		'''
		self.host = host
		self.port = port
		self.retries = retries
		self.timeout = timeout
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
		
		self.seqnum = '0' #initializing sequence number
	
	def mb_checksum(self, s): #Checksum code
		checksum = 0x0
	
		for c in s:
			ordval = ord(c)
			checksum = checksum ^ ordval
		
		return chr(checksum)
		
	def build_pckt(self, message):
		header = 'C' + self.seqnum + self.mb_checksum(message)
		return header + message
		
	def seq_switch(self):
		if self.seqnum == '0':
			self.seqnum = '1'
		else:
			self.seqnum = '0'

	def getMessages(self):
		'''
		You should make calls to get messages from the message 
		board server here.
		'''
		packet = self.build_pckt("GET")
		
		for i in range(self.retries):
			self.sock.sendto(packet, (self.host, self.port))
			(readlist, writelist, errlist) = select([self.sock], [], [], self.timeout)
			if len(readlist) > 0:
				(data, serveraddr) = readlist[0].recvfrom(1400)
				
				if data[0] == 'C':
					if data[1] == '1' or data[1] == '0': #Sequence bit uncorrupted
						if data[1] == self.seqnum:
							if data[2] == self.mb_checksum(data[3:]): #Could just AND it, but more readable this way
								self.seq_switch()
								return data
						else: #sequence number is off, server got our message already but its ACK was dropped
							return "" #Stop sending this packet
							
							
			#else: we've timed out. Repeat the loop
			
		print "Timeout on message-pull"
		
		return "AAARequest for messages dropped." #Will get thrown onto the view as a message by the Controller

	def postMessage(self, user, message):
		'''
		You should make calls to post messages to the message 
		board server here.
		'''
		packet = self.build_pckt("POST " + user + "::" + message)
		
		for i in range(self.retries):
			self.sock.sendto(packet, (self.host, self.port))
			(readlist, writelist, errlist) = select([self.sock], [], [], self.timeout)
			if len(readlist) > 0:
				(data, serveraddr) = readlist[0].recvfrom(1400)
				
				if data[0] == 'C':
					if data[1] == '1' or data[1] == '0': #Sequence bit uncorrupted
						if data[1] == self.seqnum:
							if data[2] == self.mb_checksum(data[3:]): #Could just AND it, but more readable this way
								self.seq_switch()
								return data
						else: #sequence number is off, server got our message already but its ACK was dropped
							return "" #Stop sending this packet
							
			#else: we've timed out. Repeat the loop
			
		index = packet.find("::") #Used for nice output
		print "Timeout on message:", packet[index + 2:]
		return "AAAPost dropped." #Will get thrown onto the view as a message by the Controllers	
		
class MessageBoardController(object):
	'''
	Controller class in MVC pattern that coordinates
	actions in the GUI with sending/retrieving information
	to/from the server via the MessageBoardNetwork class.
	'''

	def __init__(self, myname, host, port, retries, timeout):
		self.name = myname
		self.view = MessageBoardView(myname)
		self.view.setMessageCallback(self.post_message_callback)
		self.net = MessageBoardNetwork(host, port, retries, timeout)

	def run(self):
		self.view.after(1000, self.retrieve_messages)
		self.view.mainloop()

	def post_message_callback(self, m):
		'''
		This method gets called in response to a user typing in
		a message to send from the GUI.  It should dispatch
		the message to the MessageBoardNetwork class via the
		postMessage method.
		'''
		response = self.net.postMessage(myname, m)
		if response[3:] == "OK":
			self.view.setStatus("Message sent.")
		else: #error
			#print response + " The post is wrong"
			self.view.setStatus(response[3:]) #Slice off the header

	def retrieve_messages(self):
		'''
		This method gets called every second for retrieving
		messages from the server.  It calls the MessageBoardNetwork
		method getMessages() to do the "hard" work of retrieving
		the messages from the server, then it should call 
		methods in MessageBoardView to display them in the GUI.

		You'll need to parse the response data from the server
		and figure out what should be displayed.

		Two relevant methods are (1) self.view.setListItems, which
		takes a list of strings as input, and displays that 
		list of strings in the GUI, and (2) self.view.setStatus,
		which can be used to display any useful status information
		at the bottom of the GUI.
		'''
		self.view.after(1000, self.retrieve_messages)
		messagedata = self.net.getMessages()
		
		#if messagedata[0] == 'C' and messagedata[1] == self.net.seqnum and messagedata[2] == self.net.mb_checksum(messagedata[3:]):
		if messagedata[3:5] == "OK": # if everything went well
			messagedata = messagedata[6:] #get rid of header
			messages = messagedata.split("@") #split messages

			for i in range(1, len(messages)):
				messages[i] = "@" + " ".join(messages[i].split("::"))
			self.view.setListItems(messages) 
			self.view.setStatus("Retrieved " + str(len(messages)-1) + " messages.")
		else:
			#print messagedata + " Don't see this"
			self.view.setStatus(messagedata[3:]) #slice off header

class MessageBoardView(Tkinter.Frame):
	'''
	The main graphical frame that wraps up the chat app view.
	This class is completely written for you --- you do not
	need to modify the below code.
	'''
	def __init__(self, name):
		self.root = Tkinter.Tk()
		Tkinter.Frame.__init__(self, self.root)
		self.root.title('{} @ messenger465'.format(name))
		self.width = 80
		self.max_messages = 20
		self._createWidgets()
		self.pack()

	def _createWidgets(self):
		self.message_list = Tkinter.Listbox(self, width=self.width, height=self.max_messages)
		self.message_list.pack(anchor="n")

		self.entrystatus = Tkinter.Frame(self, width=self.width, height=2)
		self.entrystatus.pack(anchor="s")

		self.entry = Tkinter.Entry(self.entrystatus, width=self.width)
		self.entry.grid(row=0, column=1)
		self.entry.bind('<KeyPress-Return>', self.newMessage)

		self.status = Tkinter.Label(self.entrystatus, width=self.width, text="starting up")
		self.status.grid(row=1, column=1)

		self.quit = Tkinter.Button(self.entrystatus, text="Quit", command=self.quit)
		self.quit.grid(row=1, column=0)


	def setMessageCallback(self, messagefn):
		'''
		Set up the callback function when a message is generated 
		from the GUI.
		'''
		self.message_callback = messagefn

	def setListItems(self, mlist):
		'''
		mlist is a list of messages (strings) to display in the
		window.  This method simply replaces the list currently
		drawn, with the given list.
		'''
		self.message_list.delete(0, self.message_list.size())
		self.message_list.insert(0, *mlist)
		
	def newMessage(self, evt):
		'''Called when user hits entry in message window.  Send message
		to controller, and clear out the entry'''
		message = self.entry.get()  
		if len(message):
			self.message_callback(message)
		self.entry.delete(0, len(self.entry.get()))

	def setStatus(self, message):
		'''Set the status message in the window'''
		self.status['text'] = message

	def end(self):
		'''Callback when window is being destroyed'''
		self.root.mainloop()
		try:
			self.root.destroy()
		except:
			pass

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='COSC465 Message Board Client')
	parser.add_argument('--host', dest='host', type=str, default='localhost',
						help='Set the host name for server to send requests to (default: localhost)')
	parser.add_argument('--port', dest='port', type=int, default=1111,
						help='Set the port number for the server (default: 1111)')
						
	###New for Prj 2
	parser.add_argument("--retries", dest='retries', type=int, default=3, help="Set the number of retransmissions in case of a timeout")
	parser.add_argument("--timeout", dest='timeout', type=float, default=0.1, help="Set the RTO value")
	###
	args = parser.parse_args()

	myname = raw_input("What is your user name (max 8 characters)? ")

	app = MessageBoardController(myname, args.host, args.port, args.retries, args.timeout)
	app.run()


