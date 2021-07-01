##CC = g++-5
CXX = g++ 
CXXFLAGS = -Wall -O3 -std=c++11 -march=native -fopenmp -fno-ipa-cp ##-pg

LIBS = -lgomp -lpthread -lm -ldl

SOURCES := $(wildcard *.cpp)
OBJECTS := $(SOURCES:%.cpp=%.o)

all: bench_spdmv 

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

bench_spdmv: $(OBJECTS) 	
	$(CXX) -o bench_spdmv $(OBJECTS) $(LIBS)


clean:   
	rm -f *.o bench_spdmv 
