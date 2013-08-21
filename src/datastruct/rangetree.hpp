
struct point{ int x,y; };

typedef unsigned int result_t;

class rangetree{
public:

	void prepareTree(vector<point> &points);
	~rangetree();

	bool rangeSearch(unsigned int lowerX, unsigned int upperX, unsigned int lowerY, unsigned int upperY);
	bool nextY(unsigned int x, unsigned int y, result_t &result);
	bool prevY(unsigned int x, unsigned int y, result_t &result);

protected:
	//Mergesort Ys from down to up
	void mergeYs(int curIdx, unsigned int curLevel);
	bool rangeSearch_inner(unsigned int curIdx, int curLevel, unsigned int lowerX, unsigned int upperX, unsigned int lowerY, unsigned int upperY);

	bool nextBelow_inner(unsigned int curIdx, int curLevel, unsigned int x, unsigned int y, result_t &result);
	bool nextOver_inner(unsigned int curIdx, int curLevel, unsigned int x, unsigned int y, result_t &result);

	unsigned int n, height;

	unsigned int *maxX;
	unsigned int *minX;
	unsigned int *sortedYs;
	unsigned int *yPtrs;

};


	
