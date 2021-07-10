
#define PATH_TIME_SERIES "/home/christina/Desk/SAFARI/code/zsimramulator-cube-nomsg/benchmarks/timeseries/inputs/"
#define PATH_RESULTS "/home/christina/Desk/SAFARI/code/zsimramulator-cube-nomsg/benchmarks/timeseries/results/"
#define DTYPE double

typedef struct  {
  double value;
  int idx;
}profile;

int loadTimeSeriesFromFile (std::string infilename, std::vector<DTYPE> &A, int &timeSeriesLength);
int saveProfileToFile(std::string outfilename, profile  * prof,  int timeSeriesLength, int windowSize);
