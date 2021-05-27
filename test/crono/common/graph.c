#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <fcntl.h>
#include<string.h>
#include <time.h>

#include "graph.h"

// Read graph
struct Graph* graph_read(const char *filename)
{
    FILE *fp;
    fp = fopen(filename,"r");
    char line[50];
    char *token;
    long int V;
    long int dest;
    long int source;
    weight_t weight;
    long int counter = 1;
    struct Graph* graph = NULL;
    long int edges = 0;

    while ( fgets ( line, sizeof line, fp ) != NULL ) /* read a line */
    {
        token=strtok(line," ");

        if(strcmp(token,"c")==0 && counter==2)
        {
            token=strtok(NULL," ");
            // printf("Token=%s\n",token);
            token=strtok(NULL," ");
            // printf("Token=%s\n",token);
            token=strtok(NULL," ");
            //printf("Token=%s\n",token);
            token=strtok(NULL," ");
            // printf("Token=%s\n",token);
            V=atol(token);
            // printf("V=%d",V);
            graph = createGraph(V);
        }
        else if(strcmp(token,"a")==0)
        { 

            //printf("Here");
            token=strtok(NULL," ");
            source=atol(token);
            //printf("Source=%d\t",source);

            token=strtok(NULL," ");
            dest=atol(token);
            //printf("Dest=%d\n",dest);

            token=strtok(NULL," ");
            weight=atof(token);
            //printf("Weight=%d\n",weight);
            edges++;
            addEdge(graph, source - 1, dest - 1, weight);
            //addEdge(graph, source, dest, weight);

        }
        counter++;
    }   

    return graph;
}

float getRandomWeight() 
{
    return (float) (rand() % 100); 
}

// Read graph in mtx format
struct Graph* graph_read_mtx(const char *filename)
{
    FILE *fp;
    fp = fopen(filename,"r");
    char *line;
    char *token;
    long int V, El;
    int dest;
    int source;
    weight_t weight;
    long int counter = 1;
    struct Graph* graph = NULL;
    long int edges = -1;

    // Initialize for random weights
    srand((float) (time(0)));
    
    line = (char *) malloc(1000 * sizeof(char));
    
    while ( fgets ( line, 1000, fp ) != NULL ) /* read a line */
      {
        token=strtok(line," ");
        //printf("token %s\n", token);

        if(token[0] == '%')
            ;
        else if(token[0] != '%' && edges == -1){
            V = atol(token);
            token=strtok(NULL," ");
            token=strtok(NULL," ");
            El = atol(token);
            graph = createGraph(V);
            edges++;
        }else{
            source = atoi(token);
            token=strtok(NULL," ");
            dest = atoi(token);
            edges++;
            weight = 1;//getRandomWeight();//FIXME MUST=same weights in eddes!!!
            //printf("%d %d\n", source, dest);
            addEdge(graph, source - 1, dest - 1, weight);
        }
    }
 
   free(line); 
   // find_avg_degree(graph);
    return graph;
}


// A utility function to create a new adjacency list node
struct AdjListNode* newAdjListNode(long int dest, weight_t weight)
{
    struct AdjListNode* newNode =
        (struct AdjListNode*) malloc(sizeof(struct AdjListNode));
    newNode->dest = dest;
    newNode->weight = weight;
    return newNode;
}

// A utility function that creates a graph of V vertices
struct Graph* createGraph(long int V)
{
    struct Graph* graph = (struct Graph*) malloc(sizeof(struct Graph));
    graph->V = V;
    graph->edges = 0;
    graph->max_degree = 0; 
    graph->max_degree_vertex = 0; 

    // Create an array of adjacency lists.  Size of array will be V
    graph->array = (struct AdjList*) malloc(V * sizeof(struct AdjList));

    // Initialize each adjacency list as empty by making head as NULL
    for (long int i = 0; i < V; ++i){      
        graph->array[i].head = NULL;
        graph->array[i].neighboors = 0;
    }

    return graph;
}

// Adds an edge to an undirected graph
void addEdge(struct Graph* graph, long int src, long int dest, weight_t weight)
{
    // Add an edge from src to dest.  A new node is added to the adjacency
    // list of src.  The node is added at the begining
    if(graph->array[src].head==NULL) 
        graph->array[src].head = (struct AdjListNode *) malloc(sizeof(struct AdjListNode));
    else 
        graph->array[src].head = (struct AdjListNode *) realloc(graph->array[src].head, (graph->array[src].neighboors+1) * sizeof(struct AdjListNode));

    graph->array[src].head[graph->array[src].neighboors].dest = dest;
    graph->array[src].head[graph->array[src].neighboors].weight = weight;
    graph->array[src].neighboors++;
   
    if(graph->array[src].neighboors > graph->max_degree){
        graph->max_degree = graph->array[src].neighboors;
        graph->max_degree_vertex = src;
    }
    // Since graph is undirected, add an edge from dest to src also

    if(graph->array[dest].head==NULL) 
        graph->array[dest].head = (struct AdjListNode *) malloc(sizeof(struct AdjListNode));
    else 
        graph->array[dest].head = (struct AdjListNode *) realloc(graph->array[dest].head, (graph->array[dest].neighboors+1) * sizeof(struct AdjListNode));

    graph->array[dest].head[graph->array[dest].neighboors].dest = src;
    graph->array[dest].head[graph->array[dest].neighboors].weight = weight;
    graph->array[dest].neighboors++;

    if(graph->array[dest].neighboors > graph->max_degree){
        graph->max_degree = graph->array[dest].neighboors;
        graph->max_degree_vertex = dest;
    }

    graph->edges++;
}
