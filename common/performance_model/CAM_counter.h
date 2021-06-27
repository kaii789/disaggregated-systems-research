#pragma once
#include <utility> 
#include <cmath>
#include <cstring>
#include <list>
#include "boost/tuple/tuple.hpp"

class CAM_counter {

public:
unsigned long int Read(unsigned char);
void Write(unsigned char,unsigned long int);
void Update1( std::pair <bool,unsigned char>*,unsigned long int);
void Update2();
std::pair<bool,unsigned char>Search(unsigned long int);
CAM_counter(unsigned int);
~CAM_counter();
private:
unsigned long int* FV_table;
unsigned char* counter;
bool* hit_table;
std::list <unsigned long int> miss_buffer;
unsigned int _size;
};
