import zmq
import random

ctx = zmq.Context()
socket = ctx.socket(zmq.REQ)
socket.connect("tcp://127.0.0.1:5665")


def getNext(y):
	socket.send("NEXTY t206_reads %d %d" % (checkX,y))
	res = [int(x) for x in socket.recv().split(" ")]
	if res[0] == 0: raise KeyError
	return res[1]

def getPrev(y):
	socket.send("PREVY t206_reads %d %d" % (checkX, y))
	res = [int(x) for x in socket.recv().split(" ")]
	if res[0] == 0: raise KeyError
	return res[1]

while True:
	if random.randint(0,1) == 0:	
		checkX = random.randint(0x00bc0000,0x00bd0000)	
	else:
		checkX = random.randint(0x0012ff00,0x00130100)	
	l = []
	lastVal = 0
	while True:
		try:
			l.append(getNext(lastVal))
		except KeyError:
			break
		lastVal = l[-1]
	if len(l) == 0:continue
	print hex(checkX)
	print len(l)

	print "Backwards assert"
	for i in xrange(1,len(l)):
		assert l[i-1] == getPrev(l[i])
	
	excepted = False
	try:
		getPrev(l[0])
	except:
		excepted = True
	assert excepted == True

	print "Check the gaps"
	for i in xrange(len(l) -1):
		if l[i+1] - l[i] > 4:
			middle = (l[i+1] +l[i])	/ 2
			assert getNext(middle) == l[i+1]
			assert getNext(middle-1) == l[i+1]
			assert getNext(middle+1) == l[i+1]
			assert getPrev(middle) == l[i]
			assert getPrev(middle-1) == l[i]
			assert getPrev(middle+1) == l[i]
			
