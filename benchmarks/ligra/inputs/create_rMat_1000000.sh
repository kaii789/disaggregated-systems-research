#!/bin/sh

# Run this file from the ligra/inputs directory!

# Build tool that generates a rMat graph
cd ../utils
make rMatGraph

cd ../inputs
# Generate a rMat graph with 1000000 vertices, with the file called rMat_1000000
../utils/rMatGraph 1000000 rMat_1000000
