#!/bin/sh

# This script downloads the weight files we will use in one go.
# Make sure to run this script in the root "darknet" folder.

echo "Starting download..."

# Download links found on: https://pjreddie.com/darknet/imagenet/
# Darknet
wget -N https://pjreddie.com/media/files/darknet.weights

# Darknet19
wget -N https://pjreddie.com/media/files/darknet19.weights

# VGG-16
wget -N https://pjreddie.com/media/files/vgg-16.weights

# Tiny Darknet (already in original Darknet repo)
wget -N https://pjreddie.com/media/files/tiny.weights

# Resnet 50
wget -N https://pjreddie.com/media/files/resnet50.weights

# Resnet 152
# wget -N https://pjreddie.com/media/files/resnet152.weights
