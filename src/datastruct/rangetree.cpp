using namespace std;
#include <iostream>
#include <vector>
#include <algorithm>
#include <cassert>
#include <sstream>
#include <cstring>

#include "rangetree.hpp"

#define INFINITY 0xfffffff0 // XXX: What about 64-bit addresses, they might go over this

bool xSmaller(const point &p1, const point &p2){
	if(p1.x != p2.x) return (p1.x<p2.x);
	return p1.y<p2.y;
}

int bsearch_getIndex(unsigned int *arr, unsigned int count, result_t haystack){
	unsigned int low = 0, high = count - 1;
	while(low <= high && high<count){
		unsigned int middle = (high + low)/2;
		if( arr[middle] < haystack){
			low = middle + 1;
		} else if(arr[middle] > haystack){
			high = middle - 1;	
		}else{
			if( middle > 0 && arr[middle - 1] == arr[middle]){
				high = middle - 1;	
				continue;
			}
			return middle;
		}
	}
	if(low >= count) return -1;

	return low;
	//smallest x such that arr[x] >= haystack 
}

// "Does arr[0] ... arr[count] contain x such that lower <= x <= upper?"
bool bsearch_exists(unsigned int *arr, unsigned int count, unsigned int lower, unsigned int upper){
	int low = bsearch_getIndex(arr, count, lower);
	if(low == -1) return false;
	//cout << "arr[low]" << arr[low] << endl;
	return (arr[low]>= lower && arr[low] <= upper);
}

void rangetree::prepareTree(vector<point> &points){
	cerr << "Inserting " << points.size() << " entries" << endl;
	sort(points.begin(), points.end(), xSmaller);
	height = 1;
	while( (unsigned int)((1<<height)) <points.size()) 
		height++;
	n = 1<< height;	
	height++;

	cerr << "Tree height: " << height << endl;

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

rangetree::~rangetree(){
	delete[] maxX;
	delete[] minX;
	delete[] yPtrs;
	delete[] sortedYs;	
}

//Answers whether the bounding box (lowerX, lowerY) - (upperX, upperY) specified contains any points
bool rangetree::rangeSearch(unsigned int lowerX, unsigned int upperX, unsigned int lowerY, unsigned int upperY){
	return rangeSearch_inner(1, 0, lowerX, upperX, lowerY, upperY);
}

bool rangetree::rangeSearch_inner(unsigned int curIdx, int curLevel, unsigned int lowerX, unsigned int upperX, unsigned int lowerY, unsigned int upperY){
	if( (maxX[curIdx] < lowerX) || (minX[curIdx]>upperX) )
		return false;

	if( lowerX <= minX[curIdx]  && maxX[curIdx] <= upperX){

		int levelLen = n / (1 << curLevel );
		/*cerr << "Contains fully" << minX[curIdx] << "- " << maxX[curIdx] << " curIdx: " << curIdx << endl;
	}*/
	

		bool res = bsearch_exists(sortedYs + yPtrs[curIdx], levelLen, lowerY, upperY); 
 //		cerr << "bsearch yields" << res << endl;
		return res;

	}

	if(curIdx <= n){
		if(rangeSearch_inner(curIdx * 2, curLevel + 1, lowerX, upperX, lowerY, upperY))
			return true;
		if(rangeSearch_inner(curIdx * 2 + 1, curLevel + 1, lowerX, upperX, lowerY, upperY))
			return true;
	}
	return false;
}

bool rangetree::nextY(unsigned int x, unsigned int y, result_t &result){
	return nextOver_inner(1, 0, x, y, result);
}
bool rangetree::prevY(unsigned int x, unsigned int y, result_t &result){
	return nextBelow_inner(1, 0, x, y, result);
}

bool rangetree::nextBelow_inner(unsigned int curIdx, int curLevel, unsigned int x, unsigned int y, result_t &result){

	#ifdef DEBUG
	cerr << minX[curIdx] << " " << maxX[curIdx] << endl;	
	#endif
	// Prefer right until there's nothing smaller
	if( ! (minX[curIdx] <= x && x <= maxX[curIdx] )) return false;
	if( maxX[curIdx] == x && minX[curIdx] == x){
		int levelLen = n / (1 << curLevel );

/*		for(int i = 0; i < levelLen;i++)
			cerr << sortedYs[yPtrs[curIdx] + i] << " " ;
		cerr << endl;*/

		int targetElement  = bsearch_getIndex(sortedYs + yPtrs[curIdx], levelLen, y);		

		if(targetElement == -1){ // all are smaller than the target value, pick largest
			//cerr << "-1" << endl;
			result = sortedYs[yPtrs[curIdx] + levelLen - 1];
			//cerr << "returning " << result << endl;
			return true;
		}
		if(targetElement > 0){

			//cerr << ">0 " << targetElement << "(len " << levelLen << endl;
			//cerr << "targetelement = " << sortedYs[yPtrs[curIdx] + targetElement] << endl;
			result = sortedYs[yPtrs[curIdx] + targetElement - 1];
			//cerr << "returning " << result << endl;
			return true;
		}
		return false;
	}

	if(curIdx <= n){
		bool res1 = nextBelow_inner(curIdx * 2 + 1, curLevel + 1, x, y, result); // right
		if(res1) return true;

		bool res2 = nextBelow_inner(curIdx * 2, curLevel + 1, x, y, result); // left
		if(res2) return true;
	}
	return false;	
}

bool rangetree::nextOver_inner(unsigned int curIdx, int curLevel, unsigned int x, unsigned int y, result_t &result){
	// Prefer left until there's nothing smaller

	#ifdef DEBUG
	cerr << minX[curIdx] << " " << maxX[curIdx] << endl;	
	#endif 

	if( ! (minX[curIdx] <= x && x <= maxX[curIdx] )) return false;
	if( maxX[curIdx] == x && minX[curIdx] == x){
		int levelLen = n / (1 << curLevel );
		int biggerElement = bsearch_getIndex(sortedYs+yPtrs[curIdx], levelLen, y+1);		
		if(biggerElement != -1){
			result = sortedYs[yPtrs[curIdx] + biggerElement];
			return true;
		}else{
			return false;
		}
	}

	if(curIdx < n){

		if(nextOver_inner(curIdx * 2, curLevel + 1, x, y, result))
			return true;

		if(nextOver_inner(curIdx * 2 + 1, curLevel + 1, x, y, result))
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





