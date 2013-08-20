#include <iostream>
using namespace std;
#include <vector>
#include <algorithm>
#include <cassert>
#include <sstream>
#include <fstream>
#include <zmq.hpp>
#include <cstring>

unsigned int height;

struct point{
	int x,y;
};


vector<point> points;

bool xSmaller(const point &p1, const point &p2){
	if(p1.x != p2.x) return (p1.x<p2.x);
	return p1.y<p2.y;
}

void loadInput(string filename){
	int n;
	ifstream fin(filename.c_str());
	cout << "Reading input from " << filename << endl;
	fin >> n;
	for(int i = 0; i < n; i++){
		point p;
		fin >> p.x >> p.y;
		points.push_back(p);
	}
}
unsigned int n;

unsigned int *maxX;
unsigned int *minX;
unsigned int *sortedYs;
unsigned int *yPtrs;

bool  bsearch_exists(unsigned int *arr, unsigned int count, unsigned int lower, unsigned int upper){
	unsigned int low = 0, high = count - 1;
	while(low>= 0 && low <= high && high<count){
		unsigned int middle = (high + low)/2;
		//cout << low << " " << high << " " << middle << endl;
		if( arr[middle] < lower){
			low = middle + 1;
		} else if(arr[middle] > lower){
			high = middle - 1;	
		}else{
			return true; //exact match with lower bound
		}
	}
	if(low >= count) low = count - 1;
	if(low < 0) low = 0;

	//cout << "arr[low]" << arr[low] << endl;
	return (arr[low]>= lower && arr[low] <= upper);
}


bool rangeSearch(unsigned int curIdx, int curLevel, unsigned int lowerX, unsigned int upperX, unsigned int lowerY, unsigned int upperY){
	if( (maxX[curIdx] < lowerX) || (minX[curIdx]>upperX) )
		return false;
	if( lowerX <= minX[curIdx]  && maxX[curIdx] <= upperX){
		//cout << "X-wise wholly contained " << minX[curIdx] << " - " << maxX[curIdx] << endl;
		int levelLen = n / (1<<curLevel);
	/*	for(int i = 0; i < levelLen; i++){
			cout << sortedYs[yPtrs[curIdx] + i] << " ";
		} 
		cout << endl;
		cout << "lowerY: " << lowerY << " upperY:" << upperY << endl; */

		//cout << "Y-wise check: " << bsearch_exists(sortedYs + (yPtrs[curIdx] ), levelLen, lowerY, upperY) << endl; 
		bool res = bsearch_exists(sortedYs + (yPtrs[curIdx] ), levelLen, lowerY, upperY); 

		return res;

	}

	//cout << "Inspecting " << minX[curIdx] << " - " << maxX[curIdx] << endl;
	if(curIdx < n){
		if(rangeSearch(curIdx * 2, curLevel + 1, lowerX, upperX, lowerY, upperY))
			return true;
		if(rangeSearch(curIdx * 2 + 1, curLevel + 1, lowerX, upperX, lowerY, upperY))
			return true;
	}
	return false;
}


//Mergesort Ys from down to up
void mergeYs(int curIdx, unsigned int curLevel){
	if(curLevel + 1 == height) return;
	
	mergeYs(curIdx * 2,     curLevel + 1);
	mergeYs(curIdx * 2 + 1, curLevel + 1);

	//cout << "mergeYs " << curIdx << " " << curLevel << endl;
	int curLen = n / (1 << curLevel);	
	int childLen = n / (1 << (curLevel+1));

	int ptr1 = yPtrs[curIdx*2];
	int ptr2 = yPtrs[curIdx*2 + 1];
	int dstPtr = yPtrs[curIdx];

	int count1 = 0, count2 = 0 ;
	while(count1+count2 < curLen){
		assert( ! ( count1 >= childLen && count2 >= childLen ));
		//cout << "Storing to " << dstPtr << " ptr1: " << ptr1 << " ptr2: " << ptr2 << endl;
		if(count1 >= childLen){
			sortedYs[dstPtr++] = sortedYs[ptr2++];
			count2++;
			continue;
		}
		if(count2 >= childLen){
			sortedYs[dstPtr++] = sortedYs[ptr1++];
			count1++;
			continue;
		}
		if( sortedYs[ptr1] <= sortedYs[ptr2]){
			sortedYs[dstPtr++] = sortedYs[ptr1++];
			count1++;
			continue;	
		}else{
			sortedYs[dstPtr++] = sortedYs[ptr2++];
			count2++;
			continue;
		}
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

	
	loadInput(argv[1]);
	cout << points.size() << " entries" << endl;
	sort(points.begin(), points.end(), xSmaller);
	height = 1;
	while( (1<<height) <points.size()) height++;
	n = 1<< height;	
	height++;

	cout << "height: " << height << endl;

	maxX = new unsigned int[n*2];
	minX = new unsigned int[n*2];
	yPtrs = new unsigned int[n*2];
	sortedYs = new unsigned int[ n * height];

	for(unsigned int i = 0; i < n*2; i++){
		maxX[i] = 99999999; //XXX: Inf
		minX[i] = 99999999; //XXX: Inf
	}
	for(unsigned int i = 0; i < n *height; i++){
		sortedYs[i] = 999999999; //XXX: Inf
	}

	// "Allocate" sections 
	int yIdx = 0;
	unsigned int nextLevelBoundary = 2;
	int curLevel = 0;

	for(unsigned int i = 1; i <(n*2); i++){
		if(i == nextLevelBoundary){
			curLevel++;
			nextLevelBoundary <<= 1;
		}
		yPtrs[i] = yIdx;
		//cout << "[" << i << "] = " << yIdx << endl;
		yIdx += (n/(1 << curLevel));
	}


	int i = 0;
	for(vector<point>::iterator it = points.begin(); it != points.end(); it++, i++){
		maxX[n+i] = minX[n+i] = it->x;
		sortedYs[ yPtrs[ n + i ] ] = it->y;
		 // cout << it->x << ", " << it->y << endl;
	}

	for(int i = n -1; i > 0; i--){
		minX[i] = minX[2*i];
		maxX[i] = maxX[2*i+1];

	}
	mergeYs(1, 0);

	zmq::context_t context (1);
	zmq::socket_t socket(context, ZMQ_REP);
	stringstream ss;
	string s;
	ss << "tcp://127.0.0.1:" << serverPort;
	s = ss.str();
	socket.bind(s.c_str());
	cout << "Now serving requests at port " << serverPort << endl;

	unsigned int searchX1, searchX2, searchY1, searchY2;
	while(true){
		zmq::message_t request;
		socket.recv(&request);
		char* query = new char[request.size() + 1];
		memcpy(query, request.data(), request.size());
		query[request.size()] = 0;
		
		stringstream inputTokenizer, outputTokenizer;
		cout << "query:" << query << endl;

		inputTokenizer << query;

		//X:s
		inputTokenizer >> searchX1 >> searchX2;


		unsigned int startY, yIncrement, yResolution;
		inputTokenizer >> startY >> yIncrement >> yResolution;

		unsigned int yCoord = startY;
		for(int y = 0; y < yResolution;	y++){
			yCoord += yIncrement;

			searchY1 = yCoord;
			searchY2 = yCoord + yIncrement;
			outputTokenizer << rangeSearch(1, 0, searchX1, searchX2, searchY1, searchY2);
		}
		cout << "Responding with " << outputTokenizer.str() << endl;
		string outString = outputTokenizer.str();
		zmq::message_t reply (outString.length() + 1);
		strcpy((char*)reply.data(), outString.c_str());
		socket.send(reply);

		
	}
}
