// Simple server that stores 2D points in a range tree and answers
// queries sent over a ZeroMQ socket.

// Otto Ebeling, Aug 2013
// Licensed under GPL like the rest of the t-race project

// Time to create data structure: O(n log n)
// Space: O(n log n)
// Query time: O(n log^2(n)) 
// Query time could be optimized to O(n log n) using fractional cascading, but didn't bother

#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>
#include <sstream>
#include <fstream>
#include <zmq.hpp> //XXX: Add libzmq.dev to requirements
#include <cstring>
#include <map>

using namespace std;

#include "rangetree.hpp"
vector<point> points;

void loadInput(string filename){
	int n;
	ifstream fin(filename.c_str());
	cout << "Reading input from " << filename << endl;
	fin >> n;
	point p;
	for(int i = 0; i < n; i++){
		fin >> p.x >> p.y;
		points.push_back(p);
	}
}
int serverPort;

map<string, rangetree> trees;
int main(int argc, char** argv){
	if(argc < 3){
		cerr << "server port file1 file2 ..." << endl;
		return -1;
	}
	sscanf(argv[1], "%d", &serverPort);

	for(int i = 2; i < argc; i++){	
		points.clear();
		loadInput(argv[i]);
		trees[argv[i]].prepareTree(points);
	}
	zmq::context_t context (1);
	zmq::socket_t socket(context, ZMQ_REP);
	stringstream ss;
	string s;
	ss << "tcp://127.0.0.1:" << serverPort;
	s = ss.str();
	socket.bind(s.c_str());
	cout << "Now serving requests at port " << serverPort << endl;

	unsigned int searchX1, searchX2, searchY1, searchY2;
	unsigned int startY, yIncrement, yResolution;

	int x1,x2,y1,y2;
	string command;
	string xBitmapQuery("XBITMAP"), treeExistenceQuery("TREEEXISTS"), pingQuery("PING"), rangeQuery("RANGE");
	string nextYQuery("NEXTY"), prevYQuery("PREVY");
	while(true){
		zmq::message_t request;
		socket.recv(&request);
		char* query = new char[request.size() + 1];
		memcpy(query, request.data(), request.size());
		query[request.size()] = 0;
		
		stringstream inputTokenizer, outputTokenizer;
		string targetTree;
		cout << "query:" << query << endl;

		inputTokenizer << query;
		delete query;
		inputTokenizer >> command;
		if(command.compare(xBitmapQuery) == 0){	
			inputTokenizer >> targetTree;
			inputTokenizer >> searchX1 >> searchX2;
			inputTokenizer >> startY >> yIncrement >> yResolution;
		
			if( trees.find(targetTree) != trees.end()){
				unsigned int yCoord = startY;
				for(int y = 0; y < yResolution;	y++){

					searchY1 = yCoord;
					searchY2 = yCoord + yIncrement - 1;
					outputTokenizer << trees[targetTree].rangeSearch(searchX1, searchX2, searchY1, searchY2);
					yCoord += yIncrement;
				}
			}else{
				outputTokenizer << "UNKNOWN TREE";
			}
		}else if(command.compare(rangeQuery) == 0){
			inputTokenizer >> targetTree >> x1 >> x2 >> y1 >> y2;
			outputTokenizer << trees[targetTree].rangeSearch(x1,x2,y1,y2);
		}else if(command.compare(treeExistenceQuery) == 0){
			inputTokenizer >> targetTree;
			outputTokenizer << ( trees.find(targetTree) != trees.end());
		}else if(command.compare(nextYQuery) == 0){
			result_t result=0;
			inputTokenizer >> targetTree >> x1 >> y1;
			outputTokenizer << trees[targetTree].nextY(x1,y1,result) << " ";
			outputTokenizer << result;
		}else if(command.compare(prevYQuery) == 0){
			result_t result = 0;
			inputTokenizer >> targetTree >> x1 >> y1;
			outputTokenizer << trees[targetTree].prevY(x1,y1,result) << " ";
			outputTokenizer << result;

		}else if(command.compare(pingQuery) == 0){
			outputTokenizer << "PONG";
		}else{
			outputTokenizer << "UNKNOWN COMMAND";
		}
		cout << "Responding with " << outputTokenizer.str() << endl;
		string outString = outputTokenizer.str();
		zmq::message_t reply (outString.length()); //We purposefully omit the zero
		memcpy((char*)reply.data(), outString.c_str(), outString.size());
		socket.send(reply);

		
	}
}
