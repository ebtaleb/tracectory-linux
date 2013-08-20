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


int main(int argc, char** argv){
	if(argc != 3){
		cerr << "server <file> <port>" << endl;
		return -1;
	}
	stringstream temp;
	temp << argv[2];
	temp >> serverPort;

	rangetree tree;
	
	loadInput(argv[1]);
	tree.prepareTree(points);
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

	while(true){
		zmq::message_t request;
		socket.recv(&request);
		char* query = new char[request.size() + 1];
		memcpy(query, request.data(), request.size());
		query[request.size()] = 0;
		
		stringstream inputTokenizer, outputTokenizer;
		cout << "query:" << query << endl;

		inputTokenizer << query;

		inputTokenizer >> searchX1 >> searchX2;
		inputTokenizer >> startY >> yIncrement >> yResolution;

		unsigned int yCoord = startY;
		for(int y = 0; y < yResolution;	y++){
			yCoord += yIncrement;

			searchY1 = yCoord;
			searchY2 = yCoord + yIncrement;
			outputTokenizer << tree.rangeSearch(1, 0, searchX1, searchX2, searchY1, searchY2);
		}
		cout << "Responding with " << outputTokenizer.str() << endl;
		string outString = outputTokenizer.str();
		zmq::message_t reply (outString.length() + 1);
		strcpy((char*)reply.data(), outString.c_str());
		socket.send(reply);

		
	}
}
