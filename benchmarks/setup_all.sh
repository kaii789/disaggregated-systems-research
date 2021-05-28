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
# Create graph input file we'll use
echo
echo "Creating graph input file..."
cd ../inputs
./create_rMat_1000000.sh
