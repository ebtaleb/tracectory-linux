import zmq
context = zmq.Context()
class TreeServerClient:
	def __init__(self, port):
		self.socket = context.socket(zmq.REQ)
		self.socket.connect("tcp://localhost:%d" % port)
	def ping(self):
		self.socket.send("PING")
		poller = zmq.Poller()
		poller.register(self.socket, zmq.POLLIN)
		evts = poller.poll(100)
		if len(evts) == 0: return False
		return self.socket.recv() == "PONG"
	def getTree(self, treeName):
		return RangeTree(self, treeName)
	def treeExists(self, treeName):
		if not self.ping(): raise KeyError
		self.socket.send("TREEEXISTS %s" % treeName)
		res = self.socket.recv()
		return int(res)

class RangeTree:
	def __init__(self, server, name):
		self.server = server
		self.treeName = name

		if not self.server.treeExists(name):
			raise KeyError, "No such tree"
	def xBitmap(self, startX, endX, startY, yIncrement, yResolution):
		queryStr = "XBITMAP %s %d %d %d %d %d" % (self.treeName, startX, endX, startY, yIncrement, yResolution)
		self.server.socket.send(queryStr)
		res = self.server.socket.recv()
		return [int(x) for x in res if x in ("0","1")]


