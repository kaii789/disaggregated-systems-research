#!/bin/sh

# Run this file from the ligra/inputs directory!

if [ ! -f "rMat_1000000sym" ]; then
  # Build tool, if necessary, that generates a rMat graph
  cd ../utils
  make rMatGraph

  cd ../inputs
  # Generate a SYMMETRIC rMat graph with 1000000 vertices, with the file called rMat_1000000sym
  ../utils/rMatGraph -s 1000000 rMat_1000000sym && echo "Created symmetric rMat_1000000sym graph"
fi
