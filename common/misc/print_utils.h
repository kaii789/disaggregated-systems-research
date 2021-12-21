#ifndef __PRINT_UTILS_H__
#define __PRINT_UTILS_H__

#include "fixed_types.h"
#include <assert.h>
#include <iostream>
#include <sstream>
#include <vector>

#include <map>
#include <algorithm>

/* Helper to print vector percentiles, for stats output.
 * Modifies input vector by sorting it
 */
template<typename T>
void sortAndPrintVectorPercentiles(std::vector<T>& vec, std::ostringstream& percentages_buffer, std::ostringstream& counts_buffer, UInt32 num_bins = 40)
{
    std::sort(vec.begin(), vec.end());

    UInt64 index;
    T percentile;
    double percentage;
    
    // Compute individual_counts percentiles for output
    // the total number of points is 1 more than num_bins, since it includes the endpoints
    std::map<double, T> percentiles;
    for (UInt32 bin = 0; bin < num_bins; ++bin) {
        percentage = (double)bin / num_bins;
        index = (UInt64)(percentage * (vec.size() - 1));  // -1 so array indices don't go out of bounds
        percentile = vec[index];
        std::cout << "percentage: " << percentage << ", vector index: " << index << ", percentile: " << percentile << std::endl;
        percentiles.insert(std::pair<double, T>(percentage, percentile));
    }
    // Add the maximum
    percentage = 1.0;
    percentile = vec[vec.size() - 1];
    std::cout << "percentage: " << percentage << ", vector index: " << vec.size() - 1 << ", percentile: " << percentile << std::endl;
    percentiles.insert(std::pair<double, T>(percentage, percentile));
    // Print output in format that can easily be graphed in Python
    percentages_buffer << "[";
    counts_buffer << "[";
    for (auto it = percentiles.begin(); it != percentiles.end(); ++it) {
        percentages_buffer << it->first << ", ";
        counts_buffer << it->second << ", ";
    }
    percentages_buffer << "]";
    counts_buffer << "]";
}

#endif /* __PRINT_UTILS_H__ */
