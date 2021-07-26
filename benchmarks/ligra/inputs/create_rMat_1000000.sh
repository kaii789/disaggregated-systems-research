#!/bin/sh

# Run this file from the ligra/inputs directory!

if [ ! -f "rMat_1000000" ]; then
  # Build tool, if necessary, that generates a rMat graph
  cd ../utils
  make rMatGraph

  cd ../inputs
  # Generate a NON-symmetric rMat graph with 1000000 vertices, with the file called rMat_1000000
  ../utils/rMatGraph 1000000 rMat_1000000 && echo "Created non-symmetric rMat_1000000 graph"
fi
