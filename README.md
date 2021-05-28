# DisaggregatedSystemsUofT

## Setup steps
1. Compile Sniper
    ```
    # Run within the root directory 'DisaggregatedSystemsUofT'
    make
    ```

2. Compile and set up benchmarks
    ```
    # Run within the directory 'DisaggregatedSystemsUofT/benchmarks'
    # Sets up both Darknet and Ligra
    cd benchmarks
    ./setup_all.sh
    ```
    Alternatively, here are steps to setup Darknet and Ligra individually (assuming you're initially in the 'DisaggregatedSystemsUofT' directory):
    - Darknet:
        ```
        cd benchmarks/darknet
        # Compile Darknet
        make
        # Download weight files we'll use
        ./download_weights.sh
        ```
    
    - Ligra:
        ```
        cd benchmarks/ligra/apps
        # Compile Ligra
        make
        # Create graph input file we'll use
        cd ../inputs
        ./create_rMat_1000000.sh
        ```
