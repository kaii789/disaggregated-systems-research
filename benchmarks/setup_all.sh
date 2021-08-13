#!/bin/sh

# This script should be run from the 'benchmarks' directory

echo "Starting benchmarks setup:"

# Set up Darknet
# Compile Darknet
echo
echo "Compiling Darknet..."
cd darknet
make
# Download weight files we'll use
echo
echo "Downloading weight files..."
./download_weights.sh


# Set up Ligra
# Compile Ligra
echo
echo "Compiling Ligra..."
cd ../ligra/apps
make
# Create graph input file we'll use: 1 Mil vertices, a non-symmetric and a symmetric one
echo
echo "Creating graph input files..."
cd ../inputs
./create_rMat_1000000.sh
./create_rMat_1000000sym.sh

# Set up SpMV
# Compile SpMV
echo
echo "Compiling SpMV..."
cd ../../spmv
make

# Set up STREAM
# Compile STREAM
echo
echo "Compiling STREAM..."
cd ../stream
make

# Set up Crono 
echo
echo "Compiling Crono..."
cd ../crono
make


# Set up Timeseries
echo
echo "Compiling Timeseries..."
cd ../timeseries/src
make

# Set up Rodinia
echo
echo "Compiling Rodinia..."
cd ../../rodinia
make

# Set up SLS
echo
echo "Compiling SLS..."
cd ../sls/src
make

# Set up hpcg
echo
echo "Compiling HPCG..."
cd ../../hpcg/linux_serial
../configure Linux_Serial
make