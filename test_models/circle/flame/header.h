/**
 * \file  header.h
 * \brief Header for xmachine data structures and transition functions.
 */
#ifndef _HEADER_H
#define _HEADER_H

#ifdef _DEBUG_MODE
    #define ERRCHECK
#else
    #define NDEBUG
#endif

#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <limits.h>
#include <float.h>
#include "mboard.h"

/* Set ranges for FLAME write-out functions */

/*User-defined ranges*/
/*
#define FLAME_INT_MAX (int)1e+12
#define FLAME_DOUBLE_MAX 1e+12
#define FLAME_INT_MIN (int)-1e+12
#define FLAME_DOUBLE_MIN -1e+12
*/

/* Default C ranges (float.h, limits.h) */
#define FLAME_INT_MAX INT_MAX
#define FLAME_DOUBLE_MAX DBL_MAX
#define FLAME_INT_MIN INT_MIN
#define FLAME_DOUBLE_MIN -DBL_MAX

#define FLAME_TEST_PRINT_START_AND_END_OF_MODEL_FUNCTIONS 0
#define FLAME_TEST_PRINT_START_AND_END_OF_LIBMBOARD_CALLS 0
#define FLAME_USE_FILTERS_IN_SYNC 1

/*#define PAUSE printf("PAUSE - type anything to continue");i=getc(stdin);*/
#define PAUSE

#ifdef START_END
int start_simulation(void);
int end_simulation(void);
int start_iteration(void);
int end_iteration(void);
#endif


/* Checking macros */
#ifdef CHECK_MEMORY
#define CHECK_POINTER(PT) if(PT==NULL){printf("**** ERROR in Memory check 1\n");exit(1);}
#else
#define CHECK_POINTER(PT)
#endif






#define START_LOOP_OVER_Agent_AGENTS  \
    current_xmachine_Agent_holder = Agent_start_Agent_state->agents;\
    while (current_xmachine_Agent_holder) {\
	temp_xmachine_Agent_holder = current_xmachine_Agent_holder->next;\
	current_xmachine_Agent = current_xmachine_Agent_holder->agent;\
	current_xmachine->xmachine_Agent = current_xmachine_Agent;
#define END_LOOP_OVER_Agent_AGENTS \
	current_xmachine_Agent = NULL;\
	current_xmachine->xmachine_Agent = NULL;\
	current_xmachine_Agent_holder = temp_xmachine_Agent_holder;\
    }





/** \def SET_NO
 * \brief Provide access to environment variables in uppercase. */
#define SET_NO (FLAME_get_environment_variable_set_no())
/** \def RUN
 * \brief Provide access to environment variables in uppercase. */
#define RUN (FLAME_get_environment_variable_run())
/** \def CONST_RADIUS
 * \brief Provide access to environment variables in uppercase. */
#define CONST_RADIUS (FLAME_get_environment_variable_const_radius())
/** \def CONST_B
 * \brief Provide access to environment variables in uppercase. */
#define CONST_B (FLAME_get_environment_variable_const_b())
/** \def ARRAY_BLOCK_SIZE
 * \brief The block size to allocate to dynamic arrays. */
#define ARRAY_BLOCK_SIZE 10
/** \def ARRAY_GROWTH_RATE
 * \brief Growth ratio to scale size of dynamic arrays. 
 * Use golden ratio. This makes for a Fibonacci sequence, so the next allocation size 
 * is the sum of the current size and the previous size thus improving the chance of 
 * memory block reuse. It also allows for moderate rate of growth.
 */
#define ARRAY_GROWTH_RATE 1.618034


struct FLAME_output
{
	int type; /* 0=snapshot 1=Agent */
	int format; /* 0=XML */
	char * location;
	int period;
	int phase;
	int flag; /* Used when outputting to show it has been used */

	struct FLAME_output * next;
};
typedef struct FLAME_output FLAME_output;

/** \struct int_array
 * \brief Dynamic array to hold integers.
 *
 * Holds a pointer to an integer array and values for size and memory size.
 */
struct int_array
{
	int size;
	int total_size;

	int * array;
};

/** \struct float_array
 * \brief Dynamic array to hold floats.
 *
 * Holds a pointer to an float array and values for size and memory size.
 */
struct float_array
{
	int size;
	int total_size;

	float * array;
};

/** \struct double_array
 * \brief Dynamic array to hold doubles.
 *
 * Holds a pointer to a double array and values for size and memory size.
 */
struct double_array
{
	int size;
	int total_size;

	double * array;
};

/** \struct char_array
 * \brief Dynamic array to hold chars.
 *
 * Holds a pointer to a char array and values for size and memory size.
 */
struct char_array
{
	int size;
	int total_size;

	char * array;
};

/** \typedef struct int_array int_array
 * \brief Typedef for int_array struct.
 */
typedef struct int_array int_array;
/** \typedef struct float_array float_array
 * \brief Typedef for float_array struct.
 */
typedef struct float_array float_array;
/** \typedef struct double_array double_array
 * \brief Typedef for double_array struct.
 */
typedef struct double_array double_array;
/** \typedef struct char_array char_array
 * \brief Typedef for char_array struct.
 */
typedef struct char_array char_array;


/** \struct xmachine_memory_Agent
 * \brief Holds memory of xmachine Agent.
 */
struct xmachine_memory_Agent
{
	int id;	/**< X-machine memory variable id of type int. */
	double x;	/**< X-machine memory variable x of type double. */
	double y;	/**< X-machine memory variable y of type double. */
	double a;	/**< X-machine memory variable a of type double. */
	double b;	/**< X-machine memory variable b of type double. */
};

/** \struct xmachine_memory_Agent_holder
 * \brief Holds struct of memory of xmachine Agent.
 */
struct xmachine_memory_Agent_holder
{
	/*@dependent@*/ struct xmachine_memory_Agent * agent;	/**< Pointer to X-machine memory Agent. */

	/*@dependent@*/ struct xmachine_memory_Agent_holder * prev;	/**< Pointer to previous Agent agent in the list.  */
	/*@dependent@*/ struct xmachine_memory_Agent_holder * next;	/**< Pointer to next Agent agent in the list.  */
};

/** \struct xmachine_memory_Agent_holder
 * \brief Holds struct of memory of xmachine Agent.
 */
struct xmachine_memory_Agent_state
{
	/*@dependent@*/ struct xmachine_memory_Agent_holder * agents;	/**< Pointer to X-machine memory Agent. */

	int count;	/**< Number of agents that were in this state.  */
};

/** \struct xmachine
 * \brief Holds xmachines.
 */
struct xmachine
{
	/*@dependent@*/ /*@null@*/ /*@out@*/ struct xmachine_memory_Agent * xmachine_Agent;	/**< Pointer to X-machine memory of type Agent.  */
};

/** \typedef struct xmachine xmachine
 * \brief Typedef for xmachine struct.
 */
typedef struct xmachine xmachine;
/** \var typedef xmachine_memory_Agent xmachine_memory_Agent
 * \brief Typedef for xmachine_memory_Agent struct.
 */
typedef struct xmachine_memory_Agent xmachine_memory_Agent;
/** \var typedef xmachine_memory_Agent xmachine_memory_Agent
 * \brief Typedef for xmachine_memory_Agent struct.
 */
typedef struct xmachine_memory_Agent_holder xmachine_memory_Agent_holder;
/** \var typedef xmachine_memory_Agent xmachine_memory_Agent
 * \brief Typedef for xmachine_memory_Agent struct.
 */
typedef struct xmachine_memory_Agent_state xmachine_memory_Agent_state;

/** \struct location
 * \brief Holds location for calculating space partitioning .
 */
struct location
{
	double point;		/**< Point on an axis. */

	struct location * next;	/**< Pointer to next location on the list. */
};

/** \struct node_information
 * \brief Holds node information .
 */
struct node_information
{
	int node_id;	/**< Node ID. */
	double partition_data[6];	/**< Defines bounding box. */
	int neighbours[10]; /**< Defines the neighbours to this node - -99 if no neighbour */
	int agents_in_halo;	/**< Number of agents in the halo region. */
	int agent_total;	/**< Total number of agents on the node. */
	struct xmachine * agents;	/**< Pointer to list of X-machines. */

	struct node_information * next;	/**< Pointer to next node on the list. */
};


/** \typedef struct location location
 * \brief Typedef for location struct.
 */
typedef struct location location;
/** \typedef struct node_information node_information
 * \brief Typedef for node_information struct.
 */
typedef struct node_information node_information;

/** \var int set_no
* \brief A constant variable from the environment. */
int FLAME_environment_variable_set_no;
/** \var int run
* \brief A constant variable from the environment. */
int FLAME_environment_variable_run;
/** \var double const_radius
* \brief A constant variable from the environment. */
double FLAME_environment_variable_const_radius;
/** \var double const_b
* \brief A constant variable from the environment. */
double FLAME_environment_variable_const_b;
/** \var xmachine * temp_xmachine
* \brief Pointer to xmachine to initialise linked list. */
xmachine * temp_xmachine;

/** \var node_information * temp_node_info
* \brief Pointer to node_information to initialise linked list. */
node_information * temp_node_info;
/** \var char outputpath[1000]
* \brief Output path for files. */
char outputpath[1000];
/** \var long total_time
* \brief Total time for the simulation run (in seconds) */
double total_time;
/** \var int total_messages
* \brief Total messages sent between nodes for the simulation run */
int total_messages;
/** \var int totalnodes
* \brief Number of nodes */
int totalnodes;
/** \var xmachine ** p_xmachine
* \brief Pointer to first pointer of x-machine memory list */
//xmachine ** p_xmachine;
/** \var xmachine * current_xmachine
* \brief Pointer to current x-machine memory that is being processed */
xmachine * current_xmachine;
/* Pointer to current $agent_name agent */
/*@dependent@*/ /*@null@*/ /*@out@*/ xmachine_memory_Agent * current_xmachine_Agent;
/*@dependent@*/ xmachine_memory_Agent_holder * temp_xmachine_Agent_holder;
/*@dependent@*/ /*@null@*/ /*@out@*/ xmachine_memory_Agent_holder * current_xmachine_Agent_holder;
xmachine_memory_Agent_state * current_xmachine_Agent_next_state; /* New agents added to this state */
/* Pointer to list of Agent agents in state end_Agent state */
//xmachine_memory_Agent * temp_xmachine_Agent_end_Agent;
xmachine_memory_Agent_state * Agent_end_Agent_state;
/* Pointer to list of Agent agents in state start_Agent state */
//xmachine_memory_Agent * temp_xmachine_Agent_start_Agent;
xmachine_memory_Agent_state * Agent_start_Agent_state;




/** \var FLAME_output ** FLAME_outputs
* \brief Pointer to list of outputs */
FLAME_output * FLAME_outputs;
/** \var node_information * p_node_info
* \brief Pointer to first pointer of node list */
node_information ** p_node_info;
/** \var node_information * current_node
* \brief Pointer to current node */
node_information * current_node;


/** \var int node_number\n
 *  \brief Node number (not needed for serial codes) */
int node_number;



/** \var int iteration_loop
* \brief The current iteration number */
int iteration_loop;
/** \var int output_frequency
* \brief Frequency to output results */
int output_frequency;
/** \var int output_offset
* \brief Offset to output results */
int output_offset;

/** \def SPINF
* \brief Dummy inf value for space partition data. */
#define SPINF 999999.123456
/** \def RELEASE
* \brief Used to kill an agent via 'return RELEASE;'. */
#define RELEASE 1
/** \def kill_me_now
* \brief Used to kill an agent via 'kill_me_now'. */
#define kill_me_now return 1

void initialise_pointers(void);
void initialise_unit_testing(void);
FLAME_output * add_FLAME_output(FLAME_output ** outputs);
void free_FLAME_outputs(FLAME_output ** outputs);
void add_location(double point, location ** p_location);
void freelocations(location ** p_location);
void add_node(int node_id, double minx, double maxx, double miny, double maxy, double minz, double maxz);
void clean_up(int code);
void propagate_agents(void);
void propagate_messages_init(void);
void propagate_messages_complete(void);
void create_partitions(char * filename, int * itno);
void free_node_info(void);
void free_agent(void);
void freexmachines(void);
/* model datatypes */

void init_int_static_array(/*@out@*/ int * array, int size);
void init_int_array(int_array * array);
void reset_int_array(int_array * array);
void free_int_array(int_array * array);
void copy_int_array(int_array * from, int_array * to);
//void sort_int_array(int_array array);
//int quicksort_int(int array, int elements);
void add_int(int_array * array, int new_int);
void remove_int(int_array * array, int index);
void print_int_array(int_array * array);
void init_float_static_array(float * array, int size);
void init_float_array(float_array * array);
void reset_float_array(float_array * array);
void free_float_array(float_array * array);
void copy_float_array(float_array * from, float_array * to);
//void sort_float_array(float_array array);
//int quicksort_float(float array, int elements);
void add_float(float_array * array, float new_float);
void remove_float(float_array * array, int index);
void print_float_array(float_array * array);
void init_double_static_array(/*@out@*/ double* array, int size);
void init_double_array(double_array * array);
void reset_double_array(double_array * array);
void free_double_array(double_array * array);
void copy_double_array(double_array * from, double_array * to);
//void sort_double_array(double_array array);
//int quicksort_double(double array, int elements);
void add_double(double_array * array, double new_double);
void remove_double(double_array * array, int index);
void print_double_array(double_array * array);
void init_char_static_array(/*@out@*/ char * array, int size);
void init_char_array(char_array * array);
void reset_char_array(char_array * array);
void free_char_array(char_array * array);
void copy_char_array(char_array * from, char_array * to);
void add_char(char_array * array, char new_char);
void remove_char(char_array * array, int index);
char * copy_array_to_str(char_array * array);
void print_char_array(char_array * array);
int idle(void);
/* xml.c */
int read_int_static_array(char * buffer, int buffer_size, int * j, int * int_static_array, int size);
int read_float_static_array(char * buffer, int buffer_size, int * j, float * float_static_array, int size);
int read_double_static_array(char * buffer, int buffer_size, int * j, double * double_static_array, int size);
int read_char_static_array(char * buffer, int buffer_size, int * j, char * char_static_array, int size);
int read_int_dynamic_array(char * buffer, int buffer_size, int * j, int_array * int_dynamic_array);
int read_float_dynamic_array(char * buffer, int buffer_size, int * j, float_array * float_dynamic_array);
int read_double_dynamic_array(char * buffer, int buffer_size, int * j, double_array * double_dynamic_array);
int read_char_dynamic_array(char * buffer, int buffer_size, int * j, char_array * char_dynamic_array);


void readinitialstates(char * filename, char * filelocation, int * itno, double cloud_data[],
					   int partition_method, int flag);

void saveiterationdata(int iteration_number);
#ifdef __cplusplus
extern "C" {
#endif

void saveiterationdata_parquet(int iteration_number);

#ifdef __cplusplus
}
#endif


xmachine_memory_Agent_state * init_Agent_state();
xmachine_memory_Agent * init_Agent_agent();
void free_Agent_agent(xmachine_memory_Agent_holder * tmp, xmachine_memory_Agent_state * state);
void transition_Agent_agent(xmachine_memory_Agent_holder * tmp, xmachine_memory_Agent_state * from_state, xmachine_memory_Agent_state * to_state);
void add_Agent_agent_internal(xmachine_memory_Agent * agent, xmachine_memory_Agent_state * state);
void add_Agent_agent(int id, double x, double y, double a, double b);
void unittest_init_Agent_agent();
void unittest_free_Agent_agent();


void set_id(int id);
int agent_get_id(void);
double agent_get_x(void);
double agent_get_y(void);
double agent_get_z(void);
/* partitioning.c */
void partition_data(int totalnodes, xmachine ** agent_list, double cloud_data[], int partition_method);


void save_partition_data(void);
void generate_partitions(double cloud_data[], int partitions, int partition_method);

/* messageboard.c */

/* memory.c */
xmachine * add_xmachine(void);
int FLAME_get_environment_variable_set_no();
int FLAME_get_environment_variable_run();
double FLAME_get_environment_variable_const_radius();
double FLAME_get_environment_variable_const_b();


/* rules.c */
int FLAME_integer_in_array(int a, int * b, int size);

/* timing.c */
double get_time(void);

int set_xy(void);
#endif
