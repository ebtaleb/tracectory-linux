from Cycle import *
import os
from MemoryHistory import *
from pymongo import Connection as MongoClient

#traces['memcrypt'].memDumpAddr = 0x404050;
#traces['t206'].memDumpAddr = 2771222;
#traces['formatstring'].memDumpAddr = 0x4825A0;

class TargetTrace:
	def __init__(self, saveName):

		client = MongoClient()
		
		if saveName in client.database_names():
			self.db = client[saveName]
		else:
			print saveName
			raise ValueError, "File not found"

		self.meta = self.db.meta.find_one()
		self.cycleFactory = CycleFactory(self.db, self)
		self.saveName = saveName
		self.memDumpAddr = 0
		try:
			self.memDumpAddr = int(self.meta['memDumpAddr'])
		except:
			pass
		self.memory = MemoryHistory(self)

		#We aren't thread-safe, must use target.getLock() 
		#with all DB access for each request :(
		self.lock = Lock() 
	def getMaxTime(self):
		return int(self.meta["maxTime"])	
	def getLock(self):
		return self.lock
	def getCycleFactory(self):
		return self.cycleFactory
	def getMemDumpAddr(self):
		return self.memDumpAddr
	def getDB(self):
		return self.db
	def getInfoHtml(self):
		filename = "db/%s_info.html" % self.saveName
		if not os.path.exists(filename): return "No info"
		return open(filename).read()
	def getName(self):
		return str(self.saveName)

	def getMemoryHistory(self):
		return self.memory
