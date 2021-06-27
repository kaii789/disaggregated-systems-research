#include <utility> 
#include <cmath>
#include "boost/tuple/tuple.hpp"

class CAM {

public:
unsigned long int Read(unsigned char);
void Write(unsigned char,unsigned long int);
unsigned char Replace(unsigned long int);
void Update_Lru(unsigned char);
std::pair<bool,unsigned char>Search(unsigned long int);
boost::tuple<bool,unsigned char,char>Find_min_diff(unsigned long int,unsigned char);
CAM(unsigned int);
~CAM();
private:
unsigned long int* FV_table;
unsigned char* LRU;
unsigned int _size;
};
