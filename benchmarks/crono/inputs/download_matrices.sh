#!/bin/sh

# This script downloads some matrices files we will use in one go.
# Make sure to run this script in the root "crono/inputs" folder.

echo "Starting download..."

# Matrix download links found from: https://sparse.tamu.edu/
# roadNet-PA
if [ ! -f "roadNet-PA.mtx" ]; then
  echo "downloading PA"
  wget -N https://suitesparse-collection-website.herokuapp.com/MM/SNAP/roadNet-PA.tar.gz
  printf "Extracting roadNet-PA.mtx..."
  # Extract matrix directly into the inputs folder
  tar xzf roadNet-PA.tar.gz --strip-components=1
  rm "roadNet-PA.tar.gz"
fi

# roadNet-CA
if [ ! -f "roadNet-CA.mtx" ]; then
  wget -N https://suitesparse-collection-website.herokuapp.com/MM/SNAP/roadNet-CA.tar.gz
  # Extract matrix directly into the inputs folder
  printf "Extracting roadNet-CA.mtx..."
  tar xzf roadNet-CA.tar.gz --strip-components=1
  rm "roadNet-CA.tar.gz"
fi

# bcsstk32
if [ ! -f "bcsstk32.mtx" ]; then
  wget -N https://suitesparse-collection-website.herokuapp.com/MM/HB/bcsstk32.tar.gz
  printf "Extracting bcsstk32.mtx..."
  # Extract matrix directly into the inputs folder
  tar xzf bcsstk32.tar.gz --strip-components=1
  rm "bcsstk32.tar.gz"
fi

# cit-Patents (matrix is 261.7MB, .tar.gz file is 92.8MB)
if [ ! -f "cit-Patents.mtx" ]; then
  wget -N https://suitesparse-collection-website.herokuapp.com/MM/SNAP/cit-Patents.tar.gz
  printf "Extracting cit-Patents.mtx..."
  tar xzf cit-Patents.tar.gz
  mv cit-Patents/cit-Patents.mtx .
  rm -r cit-Patents
  rm "cit-Patents.tar.gz"
fi

# soc-Pokec (matrix is 424MB, .tar.gz file is 430.4MB)
if [ ! -f "soc-Pokec.mtx" ]; then
  wget -N https://suitesparse-collection-website.herokuapp.com/MM/SNAP/soc-Pokec.tar.gz
  printf "Extracting soc-Pokec.mtx..."
  tar xzf soc-Pokec.tar.gz
  mv soc-Pokec/soc-Pokec.mtx .
  rm -r soc-Pokec
  rm "soc-Pokec.tar.gz"
fi

# com-Orkut (matrix is 1.8GB, .tar.gz file is 927.8MB)
if [ ! -f "com-Orkut.mtx" ]; then
  wget -N https://suitesparse-collection-website.herokuapp.com/MM/SNAP/com-Orkut.tar.gz
  printf "Extracting com-Orkut.mtx..."
  tar xzf com-Orkut.tar.gz
  mv com-Orkut/com-Orkut.mtx .
  rm -r com-Orkut
  rm "com-Orkut.tar.gz"
fi

echo "Finished downloading and extracting all .mtx files."

