include common/make.config

RODINIA_BASE_DIR := $(shell pwd)

OMP_BIN_DIR := $(RODINIA_BASE_DIR)/bin

OMP_BASE_DIR := $(RODINIA_BASE_DIR)/openmp

OMP_DIRS  := backprop bfs cfd heartwall hotspot kmeans lavaMD leukocyte lud nn nw srad streamcluster particlefilter pathfinder

all: OMP 
	
OMP:
	cd openmp/backprop;				make;	cp backprop $(OMP_BIN_DIR)
	cd openmp/bfs;					make;	cp bfs $(OMP_BIN_DIR)
	cd openmp/cfd;					make;	cp euler3d_cpu euler3d_cpu_double pre_euler3d_cpu pre_euler3d_cpu_double $(OMP_BIN_DIR)
	cd openmp/heartwall;				make;	cp heartwall $(OMP_BIN_DIR)
	cd openmp/hotspot;				make;	cp hotspot $(OMP_BIN_DIR)
	cd openmp/kmeans/kmeans_openmp;			make;	cp kmeans $(OMP_BIN_DIR)
	cd openmp/lavaMD;				make;	cp lavaMD $(OMP_BIN_DIR)
	cd openmp/leukocyte;				make;	cp OpenMP/leukocyte $(OMP_BIN_DIR)
	cd openmp/lud;					make;	cp omp/lud_omp $(OMP_BIN_DIR)
	cd openmp/nn;					make;	cp nn $(OMP_BIN_DIR)
	cd openmp/nw;					make;	cp needle $(OMP_BIN_DIR)
	cd openmp/srad/srad_v1;				make;	cp srad $(OMP_BIN_DIR)/srad_v1
	cd openmp/srad/srad_v2;				make;   cp srad $(OMP_BIN_DIR)/srad_v2
	cd openmp/streamcluster;			make;	cp sc_omp $(OMP_BIN_DIR)
	cd openmp/particlefilter;			make;	cp particle_filter $(OMP_BIN_DIR)
	cd openmp/pathfinder;				make;	cp pathfinder $(OMP_BIN_DIR)

clean: OMP_clean 

OMP_clean:
	cd $(OMP_BIN_DIR); rm -f ./*;
	for dir in $(OMP_DIRS); do \
		$(MAKE) clean -C $(OMP_BASE_DIR)/$$dir; \
	done
