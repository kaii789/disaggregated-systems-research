#ifndef __GRAPH_H_
#define __GRAPH_H_

#if INT
typedef int weight_t;
#else
typedef float weight_t;
#endif

struct AdjListNode
{
    int dest;
    weight_t weight;
};

// A structure to represent an adjacency liat
struct AdjList
{
    int neighboors;
    struct AdjListNode *head;  // pointer to head node of list
};

// A structure to represent a graph. A graph is an array of adjacency lists.
// Size of array will be V (number of vertices in graph)
struct Graph
{
    long int V;
    long int edges;
    long int max_degree;
    long int max_degree_vertex;
    struct AdjList* array;
};

extern struct Graph* graph_read(const char *filename);
extern struct Graph* graph_read_mtx(const char *filename);
extern struct AdjListNode* newAdjListNode(long int dest, weight_t weight);
extern struct Graph* createGraph(long int V);
extern void addEdge(struct Graph* graph, long int src, long int dest, weight_t weight);
#endif
