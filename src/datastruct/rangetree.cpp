
using namespace std;
#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>
#include <sstream>
#include <fstream>
#include <cstring>

#include "rangetree.hpp"

#define INFINITY 999999999 // XXX: What about 64-bit addresses, they might go over this

bool xSmaller(const point &p1, const point &p2){
	if(p1.x != p2.x) return (p1.x<p2.x);
	return p1.y<p2.y;
}

	// "Does arr[0] ... arr[count] contain x such that lower <= x <= upper?"
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




void rangetree::prepareTree(vector<point> &points){
		cout << points.size() << " entries" << endl;
		sort(points.begin(), points.end(), xSmaller);
		height = 1;
		while( (1<<height) <points.size()) height++;
		n = 1<< height;	
		height++;

		cout << "height: " << height << endl;

		maxX = new unsigned int[n*2]; 	minX = new unsigned int[n*2]; 	yPtrs = new unsigned int[n*2];
		sortedYs = new unsigned int[ n * height];

		for(unsigned int i = 0; i < n*2; i++)
			maxX[i] = minX[i] = INFINITY;

		for(unsigned int i = 0; i < n *height; i++)
			sortedYs[i] = INFINITY;

		// "Allocate" sotredYs for each x-wise node and store
		// the allocated indexes into yPtrs
		int yIdx = 0;
		unsigned int nextLevelBoundary = 2;
		int curLevel = 0;

		for(unsigned int i = 1; i <(n*2); i++){
			if(i == nextLevelBoundary){
				curLevel++;
				nextLevelBoundary <<= 1;
			}
			yPtrs[i] = yIdx;
			yIdx += (n/(1 << curLevel));
		}

		//Init the leafs
		int i = 0;
		for(vector<point>::iterator it = points.begin(); it != points.end(); it++){
			maxX[n+i] = minX[n+i] = it->x;
			sortedYs[ yPtrs[ n + i ] ] = it->y;
			i++;
		}

		//Prepare the x-wise BST
		for(int i = n - 1; i > 0; i--){
			minX[i] = minX[2 * i];
			maxX[i] = maxX[2 * i + 1];
		}
		
		//Mergesort Y-lists
		mergeYs(1, 0);

	}

	//Answers whether the bounding box (lowerX, lowerY) - (upperX, upperY) specified contains any points
	bool rangetree::rangeSearch(unsigned int curIdx, int curLevel, unsigned int lowerX, unsigned int upperX, unsigned int lowerY, unsigned int upperY){
		if( (maxX[curIdx] < lowerX) || (minX[curIdx]>upperX) )
			return false;

		if( lowerX <= minX[curIdx]  && maxX[curIdx] <= upperX){
			int levelLen = n / (1 << curLevel );
			bool res = bsearch_exists(sortedYs + yPtrs[curIdx], levelLen, lowerY, upperY); 
			return res;

		}

		if(curIdx < n){
			if(rangeSearch(curIdx * 2, curLevel + 1, lowerX, upperX, lowerY, upperY))
				return true;
			if(rangeSearch(curIdx * 2 + 1, curLevel + 1, lowerX, upperX, lowerY, upperY))
				return true;
		}
		return false;
	}

	


	//Mergesort Ys from down to up
	void rangetree::mergeYs(int curIdx, unsigned int curLevel){
		if(curLevel + 1 == height) return;

		//Force post-order traversal	
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
			}
			if(count2 >= childLen){
				sortedYs[dstPtr++] = sortedYs[ptr1++];
				count1++;
			}
			if( sortedYs[ptr1] <= sortedYs[ptr2]){
				sortedYs[dstPtr++] = sortedYs[ptr1++];
				count1++;
			}else{
				sortedYs[dstPtr++] = sortedYs[ptr2++];
				count2++;
			}
		}
	}





