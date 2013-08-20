
struct point{ int x,y; };

class rangetree{
public:

	void prepareTree(vector<point> &points);
	bool rangeSearch(unsigned int curIdx, int curLevel, unsigned int lowerX, unsigned int upperX, unsigned int lowerY, unsigned int upperY);

private:
	//Mergesort Ys from down to up
	void mergeYs(int curIdx, unsigned int curLevel);
	
	unsigned int n, height;

	unsigned int *maxX;
	unsigned int *minX;
	unsigned int *sortedYs;
	unsigned int *yPtrs;

};


	
