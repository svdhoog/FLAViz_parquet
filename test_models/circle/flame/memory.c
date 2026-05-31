/**
 * \file  memory.c
 * \brief Holds memory functions.
 */

#include "header.h"


void unittest_set_xy_start_Agent_end_Agent()
{
	
	
	//return set_xy();
}


void free_messages()
{
	
}

/** \fn void initialise_pointers()
 * \brief Initialises pointers to xmachine, message, and node lists.
 */
void initialise_pointers()
{

	Agent_end_Agent_state = init_Agent_state();

	Agent_start_Agent_state = init_Agent_state();

	temp_node_info = NULL;
	p_node_info = &temp_node_info;
}

/** \fn void initialise_unit_testing()
 * \brief Initialises framework for unit testing.
 */
void initialise_unit_testing()
{
	int rc;

	rc = MB_Env_Init();
	#ifdef ERRCHECK
	if (rc != MB_SUCCESS)
	{
	   fprintf(stderr, "ERROR: Failed to initialise Message Board environment\n");
	   switch(rc) {
	       case MB_ERR_MPI:
	           fprintf(stderr, "\t reason: MPI library not initialised\n");
	           break;
	       case MB_ERR_MEMALLOC:
	           fprintf(stderr, "\t reason: out of memory\n");
	           break;
	       default:
               fprintf(stderr, "\t MB_Env_Init returned error code: %d (see libmboard docs for details)\n", rc);
               break;
	       }

	       
       	   exit(rc);

	}
	#endif

	initialise_pointers();
}

FLAME_output * add_FLAME_output(FLAME_output ** outputs)
{
	FLAME_output * current;

	current = (FLAME_output *)malloc(sizeof(FLAME_output));
	CHECK_POINTER(current);
	current->next = *outputs;
	*outputs = current;

	current->type = -1;
	current->format = -1;
	current->location = NULL;
	current->period = -1;
	current->phase = -1;
	current->flag = 0;

	return current;
}

void free_FLAME_outputs(FLAME_output ** outputs)
{
	FLAME_output * current, * next;

	current = *outputs;
	while(current)
	{
		next = current->next;
		free(current->location);
		free(current);
		current = next;
	}
	*outputs = NULL;
}

/* add_location */
/** \fn void add_location(double point, location ** p_location)
 * \brief Adds a location in order into the location list.
 * \param point Position of an agent.
 * \param p_location Pointer Pointer to the location list.
 */
void add_location(double point, location ** p_location)
{
	location * current = *p_location;
	location * tmp = NULL;
	location * newlocation = NULL;
	int found = 0;

	while(found == 0)
	{
		if(current == NULL) found = 1;
		else if(point > current->point) found = 1;
		else
		{
			tmp = current;
			current = current->next;
		}
	}

	newlocation = (location *)malloc(sizeof(location));
	CHECK_POINTER(newlocation);
	if(tmp)
	{
		tmp->next = newlocation;
	}
	else
	{
		*p_location = newlocation;
	}

	newlocation->next = current;
	newlocation->point = point;
}

/* freelocations */
/** \fn void freelocations(location ** p_location)
 * \brief Free locations from the location list.
 * \param p_location Pointer Pointer to the location list.
 */
void freelocations(location ** p_location)
{
	location * head = *p_location;
	location * tmp = NULL;

	while(head)
	{
		tmp = head->next;
		free(head);
		head = tmp;
	}

	*p_location = NULL;
}

void init_int_static_array(/*@out@*/ int * array, int size)
{
	int i;

	for(i = 0; i < size; i++) array[i] = 0;
}

void init_float_static_array(/*@out@*/ float * array, int size)
{
	int i;

	for(i = 0; i < size; i++) array[i] = 0.0;
}

void init_double_static_array(/*@out@*/ double* array, int size)
{
	int i;

	for(i = 0; i < size; i++) array[i] = 0.0;
}

void init_char_static_array(/*@out@*/ char * array, int size)
{
	int i;

	for(i = 0; i < size; i++) array[i] = '\0';
}




xmachine_memory_Agent_state * init_Agent_state()
{
	xmachine_memory_Agent_state * current = (xmachine_memory_Agent_state *)malloc(sizeof(xmachine_memory_Agent_state));
	CHECK_POINTER(current);

	current->agents = NULL;
	current->count = 0;

	return current;
}

xmachine_memory_Agent * init_Agent_agent()
{
	xmachine_memory_Agent * current = (xmachine_memory_Agent *)malloc(sizeof(xmachine_memory_Agent));
	CHECK_POINTER(current);

	current->id = 0;
	current->x = 0.0;
	current->y = 0.0;
	current->a = 0.0;
	current->b = 0.0;

	return current;
}

void free_Agent_agent(xmachine_memory_Agent_holder * tmp, xmachine_memory_Agent_state * state)
{
	if(tmp->prev == NULL) state->agents = tmp->next;
	else tmp->prev->next = tmp->next;
	if(tmp->next != NULL) tmp->next->prev = tmp->prev;

	

	free(tmp->agent);
	free(tmp);
}

void unittest_init_Agent_agent()
{
	current_xmachine_Agent = (xmachine_memory_Agent *)malloc(sizeof(xmachine_memory_Agent));
	CHECK_POINTER(current);

		current_xmachine_Agent->id = 0;
		current_xmachine_Agent->x = 0.0;
		current_xmachine_Agent->y = 0.0;
		current_xmachine_Agent->a = 0.0;
		current_xmachine_Agent->b = 0.0;
	
}

void unittest_free_Agent_agent()
{
	
	free(current_xmachine_Agent);
}

void free_Agent_agents()
{
	current_xmachine_Agent_holder = Agent_end_Agent_state->agents;
	while(current_xmachine_Agent_holder)
	{
		temp_xmachine_Agent_holder = current_xmachine_Agent_holder->next;
		free_Agent_agent(current_xmachine_Agent_holder, Agent_end_Agent_state);
		current_xmachine_Agent_holder = temp_xmachine_Agent_holder;
	}
	Agent_end_Agent_state->count = 0;
	current_xmachine_Agent_holder = Agent_start_Agent_state->agents;
	while(current_xmachine_Agent_holder)
	{
		temp_xmachine_Agent_holder = current_xmachine_Agent_holder->next;
		free_Agent_agent(current_xmachine_Agent_holder, Agent_start_Agent_state);
		current_xmachine_Agent_holder = temp_xmachine_Agent_holder;
	}
	Agent_start_Agent_state->count = 0;
}

void free_Agent_states()
{
	free(Agent_end_Agent_state);
	free(Agent_start_Agent_state);
}

void transition_Agent_agent(xmachine_memory_Agent_holder * tmp, xmachine_memory_Agent_state * from_state, xmachine_memory_Agent_state * to_state)
{
	if(tmp->prev == NULL) from_state->agents = tmp->next;
	else tmp->prev->next = tmp->next;
	if(tmp->next != NULL) tmp->next->prev = tmp->prev;

	add_Agent_agent_internal(tmp->agent, to_state);
	free(tmp);
}

void add_Agent_agent_internal(xmachine_memory_Agent * agent, xmachine_memory_Agent_state * state)
{
	xmachine_memory_Agent_holder * current = (xmachine_memory_Agent_holder *)malloc(sizeof(xmachine_memory_Agent_holder));
	CHECK_POINTER(current);

	current->next = state->agents;
	current->prev = NULL;
	state->agents = current;
	if(current->next != NULL) current->next->prev = current;
	current->agent = agent;

	state->count++;

}

/** \fn void add_Agent_agent(int id, double x, double y, double a, double b)
 * \brief Add Agent X-machine to the current being used X-machine list.
 * \param id Variable for the X-machine memory.
 * \param x Variable for the X-machine memory.
 * \param y Variable for the X-machine memory.
 * \param a Variable for the X-machine memory.
 * \param b Variable for the X-machine memory.
 */
void add_Agent_agent(int id, double x, double y, double a, double b)
{
	xmachine_memory_Agent * current;

	current = init_Agent_agent();
	/* new line added to handle dynamic agent creation*/
	current_xmachine_Agent_next_state = Agent_start_Agent_state;
	add_Agent_agent_internal(current, current_xmachine_Agent_next_state);

	current->id = id;
	current->x = x;
	current->y = y;
	current->a = a;
	current->b = b;
}


/* freexmachines */
/** \fn void freexmachines()
 * \brief Free the currently being used X-machine list.
 */
void freexmachines()
{
	free_Agent_agents();
	
}


/** \fn void set_id(int id)
 * \brief Set id memory variable for current X-machine.
 * \param id New value for variable.
 */
void set_id(int id)
{
	if(current_xmachine->xmachine_Agent)
	{
		assert(id < FLAME_DOUBLE_MAX);
		assert(id > FLAME_DOUBLE_MIN);
		(*current_xmachine->xmachine_Agent).id = id;
	}
}

/** \fn int get_id()
 * \brief Get id memory variable from current X-machine.
 * \return Value for variable.
 */
int get_id()
{
	if(current_xmachine->xmachine_Agent) return (*current_xmachine->xmachine_Agent).id;

    // suppress compiler warning by returning dummy value /
    // this statement should rightfully NEVER be reached /
    return (int)0;
}

/** \fn void set_x(double x)
 * \brief Set x memory variable for current X-machine.
 * \param x New value for variable.
 */
void set_x(double x)
{
	if(current_xmachine->xmachine_Agent)
	{
		assert(x < FLAME_DOUBLE_MAX);
		assert(x > FLAME_DOUBLE_MIN);
		(*current_xmachine->xmachine_Agent).x = x;
	}
}

/** \fn double get_x()
 * \brief Get x memory variable from current X-machine.
 * \return Value for variable.
 */
double get_x()
{
	if(current_xmachine->xmachine_Agent) return (*current_xmachine->xmachine_Agent).x;

    // suppress compiler warning by returning dummy value /
    // this statement should rightfully NEVER be reached /
    return (double)0;
}

/** \fn void set_y(double y)
 * \brief Set y memory variable for current X-machine.
 * \param y New value for variable.
 */
void set_y(double y)
{
	if(current_xmachine->xmachine_Agent)
	{
		assert(y < FLAME_DOUBLE_MAX);
		assert(y > FLAME_DOUBLE_MIN);
		(*current_xmachine->xmachine_Agent).y = y;
	}
}

/** \fn double get_y()
 * \brief Get y memory variable from current X-machine.
 * \return Value for variable.
 */
double get_y()
{
	if(current_xmachine->xmachine_Agent) return (*current_xmachine->xmachine_Agent).y;

    // suppress compiler warning by returning dummy value /
    // this statement should rightfully NEVER be reached /
    return (double)0;
}

/** \fn void set_a(double a)
 * \brief Set a memory variable for current X-machine.
 * \param a New value for variable.
 */
void set_a(double a)
{
	if(current_xmachine->xmachine_Agent)
	{
		assert(a < FLAME_DOUBLE_MAX);
		assert(a > FLAME_DOUBLE_MIN);
		(*current_xmachine->xmachine_Agent).a = a;
	}
}

/** \fn double get_a()
 * \brief Get a memory variable from current X-machine.
 * \return Value for variable.
 */
double get_a()
{
	if(current_xmachine->xmachine_Agent) return (*current_xmachine->xmachine_Agent).a;

    // suppress compiler warning by returning dummy value /
    // this statement should rightfully NEVER be reached /
    return (double)0;
}

/** \fn void set_b(double b)
 * \brief Set b memory variable for current X-machine.
 * \param b New value for variable.
 */
void set_b(double b)
{
	if(current_xmachine->xmachine_Agent)
	{
		assert(b < FLAME_DOUBLE_MAX);
		assert(b > FLAME_DOUBLE_MIN);
		(*current_xmachine->xmachine_Agent).b = b;
	}
}

/** \fn double get_b()
 * \brief Get b memory variable from current X-machine.
 * \return Value for variable.
 */
double get_b()
{
	if(current_xmachine->xmachine_Agent) return (*current_xmachine->xmachine_Agent).b;

    // suppress compiler warning by returning dummy value /
    // this statement should rightfully NEVER be reached /
    return (double)0;
}


/** \fn double agent_get_range()
 * \brief Fixed routine to get the range from current X-machine
  * \return Value of range
  */
double agent_get_range()
{
    double value = 0.0;
    /*if (current_xmachine->xmachine_Agent) value = current_xmachine->xmachine_Agent->;*/

    return value;
}

/** \fn int agent_get_id()
 * \brief Fixed routine to get the id for the current X-machine
  * \return Value of agent id
  */
int agent_get_id()
{
    int value = 0;
    /*if (current_xmachine->xmachine_Agent) value = current_xmachine->xmachine_Agent->id;*/

    return value;
}

/** \fn double agent_get_x()
 * \brief Fixed routine to get the x coordinate from current X-machine
  * \return Value of x coordinate
  */
double agent_get_x()
{
    double value = 0.0;
    /*if (current_xmachine->xmachine_Agent) value = current_xmachine->xmachine_Agent->x;*/

    return value;
}
/** \fn double agent_get_y()
 * \brief Fixed routine to get the y coordinate from current X-machine
  * \return Value of y coordinate
  */
double agent_get_y()
{
    double value = 0.0;
    /*if (current_xmachine->xmachine_Agent) value = current_xmachine->xmachine_Agent->y;*/

    return value;
}
/** \fn double agent_get_z()
 * \brief Fixed routine to get the z coordinate from current X-machine
  * \return Value of z coordinate
  */
double agent_get_z()
{
    double value = 0.0;

    return value;
}

/** \fn void add_node(int node_id, double minx, double maxx, double miny, double maxy, double minz, double maxz)
 * \brief Add a node to the node list.
 * \param node_id The node ID.
 * \param minx The minumum value on the x-axis of the bounding volume.
 * \param maxx The maximum value on the x-axis of the bounding volume.
 * \param miny The minumum value on the y-axis of the bounding volume.
 * \param maxy The maximum value on the y-axis of the bounding volume.
 * \param minz The minumum value on the z-axis of the bounding volume.
 * \param maxz The maximum value on the z-axis of the bounding volume.
 */
void add_node(int node_id, double minx, double maxx, double miny, double maxy, double minz, double maxz)
{
	node_information * current = *p_node_info;
	node_information * tmp = NULL;

	while(current)
	{
		tmp = current;
		current = current->next;
	}

	current = (node_information *)malloc(sizeof(node_information));
		CHECK_POINTER(current);

	if(tmp)
	{
		tmp->next = current;
	}
	else
	{
		*p_node_info = current;
	}

	current->next = NULL;
	current->node_id = node_id;
	current->agents_in_halo = 0;
	current->agent_total = 0;
	current->agents = NULL;


	current->partition_data[0] = minx;
	current->partition_data[1] = maxx;
	current->partition_data[2] = miny;
	current->partition_data[3] = maxy;
	current->partition_data[4] = minz;
	current->partition_data[5] = maxz;
}

/**\fn void free_node_info()
 * \brief Free the node list.
 */
void free_node_info()
{
	node_information * tmp, * head;
	head = *p_node_info;

	while(head)
	{
		tmp = head->next;
		free(head);
		head = tmp;
	}

	*p_node_info = NULL;
}

/** \fn void clean_up(int code)
 * \brief Add a node to the node list.
 * \param code The error code (zero is no error).
 */
void clean_up(int code)
{
    int rc;
	FILE *file;
	char data[1000];

	free(current_xmachine);
	/* Free x-machine memory */
	freexmachines();
	/* Free space partitions linked list */
	free_node_info();
	/* Free output list */
	free_FLAME_outputs(&FLAME_outputs);
	/* Free agent states */
	free_Agent_states();


	/* Free index maps */


	/* Free message boards */


    rc = MB_Env_Finalise();
    #ifdef ERRCHECK
    if (rc != MB_SUCCESS)
    {
       fprintf(stderr, "ERROR: Could not finalise MB environment\n");
       switch(rc) {
           case MB_ERR_ENV:
               fprintf(stderr, "\t reason: MB environment not yet started?\n");
               break;
	       default:
               fprintf(stderr, "\t MB_Env_Finalise returned error code: %d (see libmboard docs for details)\n", rc);
               break;
	       }

	       
       	   exit(rc);
    }
    #endif



	/* Write log file */
	// Check if outputpath leaves enough room for "log.xml" (7 bytes) + null terminator (1 byte)
	if (strlen(outputpath) + 8 > sizeof(data)) {
	    fprintf(stderr, "Error: outputpath is too long for the log file path buffer.\n");
	    // Handle the error gracefully (e.g., return, exit, or fall back)
	    exit(0); 
	}
	// GCC now knows this snprintf will never truncate, still we use pragma's to shut up the compiler
	#pragma GCC diagnostic push
	#pragma GCC diagnostic ignored "-Wformat-truncation"
	snprintf(data, sizeof(data), "%slog.xml", outputpath); /* use snprintf to protect against overflow */
	#pragma GCC diagnostic pop

	file = fopen(data, "a");
	fputs("<!-- <totaltime> unit: seconds -->\n", file);
	fputs("<totaltime>", file);
	sprintf(data, "%.3f", total_time);
	fputs(data, file);
	fputs("</totaltime>\n", file);
	/*fputs("<totalmessages>", file);
	sprintf(data, "%i", total_messages);
	fputs(data, file);
	fputs("</totalmessages>", file);*/
	fputs("</model_run>", file);
	fclose(file);


	if(code != 0)
	{
		printf("*** Error: ");
		if(code == 100) printf("cannot handle specified number of space partitions");
		if(code == 101) printf("could not find number of space partitions config in file");

		printf(" ***");
		exit(0);
	}
}



/** \fn int_array * init_int_array()
 * \brief Allocate memory for a dynamic integer array.
 * \return int_array Pointer to the new dynamic integer array.
 */
void init_int_array(int_array * array)
{
	(*array).size = 0;
	(*array).total_size = ARRAY_BLOCK_SIZE;
	(*array).array = (int *)malloc(ARRAY_BLOCK_SIZE * sizeof(int));
	CHECK_POINTER((*array).array);
}

/** \fn void reset_int_array(int_array * array)
* \brief Reset the int array to hold nothing.
* \param array Pointer to the dynamic integer array.
*/
void reset_int_array(int_array * array)
{
	(*array).size = 0;
}

/** \fn void free_int_array(int_array * array)
* \brief Free the memory of a dynamic integer array.
* \param array Pointer to the dynamic integer array.
*/
void free_int_array(int_array * array)
{
	free((*array).array);
}

void copy_int_array(int_array * from, int_array * to)
{
	int i;
	//to = init_int_array();

	for (i = 0; i < (*from).size; i++)
	{
		add_int(to, (*from).array[i]);
	}
}

/** \fn void sort_int_array(int_array * array)
* \brief Sort the elements of a dynamic integer array with smallest first.
* \param array Pointer to the dynamic integer array.
*/
/*void sort_int_array(int_array * array)
{
	int i, j, temp;

	for(i=0; i<((*array).size-1); i++)
	{
		for(j=0; j<((*array).size-1)-i; j++)
		{
			if(*((*array).array+j+1) < *((*array).array+j))
			{
                temp = *((*array).(*array)+j);
                *((*array).array+j) = *((*array).array+j+1);
                *((*array).array+j+1) = temp;
			}
		}
	}
}*/

/** \fn int quicksort_int(int *array, int elements)
 *  \brief Sorts the elements of the integer array in ascending order.
 *  \param Pointer to integer array
 *  \param Number of elements that must be sorted
 *  \return integer value indicating success(0) or failure(1)
 */
/*int quicksort_int(int array, int elements)
{
	#define  LEVEL  1000
	int  pivot, begin[LEVEL], end[LEVEL], i=0, left, right ;
	begin[0]=0; end[0]=elements;
	while (i>=0)
	{
		left=begin[i]; right=end[i]-1;
		if (left<right)
		{
			pivot=array[left]; if (i==LEVEL-1) return 1;
			while (left<right)
			{
				while (array[right]>=pivot && left<right) right--;
				if (left<right) array[left++]=array[right];
				while (array[left]<=pivot && left<right) left++;
				if (left<right) array[right--]=array[left];
			}
			array[left]=pivot;
			begin[i+1]=left+1;
			end[i+1]=end[i];
			end[i++]=left;
		}
	    else
	    {
	      i--;
	    }
	}
	return 0;
}*/

/** \fn void add_int(int_array * array, int new_int)
* \brief Add an integer to the dynamic integer array.
* \param array Pointer to the dynamic integer array.
* \param new_int The integer to add
*/
void add_int(int_array * array, int new_int)
{
	if((*array).size == (*array).total_size)
	{
		(*array).total_size = (int)((*array).total_size * ARRAY_GROWTH_RATE);
		(*array).array = (int *)realloc((*array).array, ((*array).total_size * sizeof(int)));
	}
	(*array).array[(*array).size] = new_int;
	(*array).size++;
}

/** \fn void remove_int(int_array * array, int index)
 * \brief Remove an integer from a dynamic integer array.
 * \param array Pointer to the dynamic integer array.
 * \param index The index of the integer to remove.
 */
void remove_int(int_array * array, int index)
{
	int i;

	if(index < (*array).size)
	{
		/* memcopy?? */
		for(i = index; i < (*array).size - 1; i++)
		{
			(*array).array[i] = (*array).array[i+1];
		}
		(*array).size--;
	}
}

/** \fn void print_int_array(int_array * array)
 * \brief Print the elements of a dynamic integer array.
 * \param array Pointer to the dynamic integer array.
 */
void print_int_array(int_array * array)
{
	int i;

	for(i=0; i<(*array).size; i++)
	{
		printf("%d> %d", i, (*array).array[i]);
	}
}

/** \fn float_array * init_float_array()
 * \brief Allocate memory for a dynamic float array.
 * \return float_array Pointer to the new dynamic float array.
 */
void init_float_array(float_array * array)
{
	(*array).size = 0;
	(*array).total_size = ARRAY_BLOCK_SIZE;
	(*array).array = (float *)malloc(ARRAY_BLOCK_SIZE * sizeof(float));
	CHECK_POINTER((*array).array);
}

/** \fn void reset_float_array(float_array * array)
* \brief Reset the float array to hold nothing.
* \param array Pointer to the dynamic float array.
*/
void reset_float_array(float_array * array)
{
	(*array).size = 0;
}

/** \fn void free_float_array(float_array * array)
* \brief Free the memory of a dynamic float array.
* \param array Pointer to the dynamic float array.
*/
void free_float_array(float_array * array)
{
	free((*array).array);
}

void copy_float_array(float_array * from, float_array * to)
{
	int i;
	//to = init_float_array();

	for (i = 0; i < (*from).size; i++)
	{
		add_float(to, (*from).array[i]);
	}
}

/** \fn void sort_float_array(float_array * array)
* \brief Sort the elements of a dynamic float array with smallest first.
* \param array Pointer to the dynamic float array.
*/
/*void sort_float_array(float_array array)
{
	int i, j;
	float temp;
	// Using bubble sorts nested loops //
	for(i=0; i<(array.size-1); i++)
	{
		for(j=0; j<(array.size-1)-i; j++)
		{
			// Comparing the values between neighbours //
			if(*(array.array+j+1) < *(array.array+j))
			{
                // Swap neighbours //
                temp = *(array.array+j);
                *(array.array+j) = *(array.array+j+1);
                *(array.array+j+1) = temp;
			}
		}
	}
}*/

/** \fn int quicksort_float(float *array, int elements)
 *  \brief Sorts the elements of the float array in ascending order.
 *  \param Pointer to float array
 *  \param Number of elements that must be sorted
 *  \return integer value indicating success(0) or failure(1)
 */
/*int quicksort_float(float array, int elements)
{
	#define  LEVEL  1000
	int i=0, left, right ;
	float pivot, begin[LEVEL], end[LEVEL];
	begin[0]=0; end[0]=elements;
	while (i>=0)
	{
		left=begin[i]; right=end[i]-1;
		if (left<right)
		{
			pivot=array[left]; if (i==LEVEL-1) return 1;
			while (left<right)
			{
				while (array[right]>=pivot && left<right) right--;
				if (left<right) array[left++]=array[right];
				while (array[left]<=pivot && left<right) left++;
				if (left<right) array[right--]=array[left];
			}
			array[left]=pivot;
			begin[i+1]=left+1;
			end[i+1]=end[i];
			end[i++]=left;
		}
	    else
	    {
	      i--;
	    }
	}
	return 0;
}*/

/** \fn void add_float(float_array * array, float new_float)
* \brief Add an floateger to the dynamic float array.
* \param array Pointer to the dynamic float array.
* \param new_float The float to add
*/
void add_float(float_array * array, float new_float)
{
	if((*array).size == (*array).total_size)
	{
		(*array).total_size = (int)((*array).total_size * ARRAY_GROWTH_RATE);
		(*array).array = (float *)realloc((*array).array, ((*array).total_size * sizeof(float)));
	}
	(*array).array[(*array).size] = new_float;
	(*array).size++;
}

/** \fn void remove_float(float_array * array, int index)
 * \brief Remove an floateger from a dynamic float array.
 * \param array Pointer to the dynamic float array.
 * \param index The index of the float to remove.
 */
void remove_float(float_array * array, int index)
{
	int i;

	if(index < (*array).size)
	{
		/* memcopy?? */
		for(i = index; i < (*array).size - 1; i++)
		{
			(*array).array[i] = (*array).array[i+1];
		}
		(*array).size--;
	}
}

/** \fn void print_float_array(float_array * array)
 * \brief Print the elements of a dynamic float array.
 * \param array Pointer to the dynamic float array.
 */
void print_float_array(float_array * array)
{
	int i;
	/* printf(""); // compiler does not like empty prfloats */
	for(i=0; i<(*array).size; i++)
	{
		printf("%d> %f", i, (*array).array[i]);
	}
}

/** \fn double_array * init_double_array()
 * \brief Allocate memory for a dynamic double array.
 * \return double_array Pointer to the new dynamic double array.
 */
void init_double_array(double_array * array)
{
	(*array).size = 0;
	(*array).total_size = ARRAY_BLOCK_SIZE;
	(*array).array = (double *)malloc(ARRAY_BLOCK_SIZE * sizeof(double));
	CHECK_POINTER((*array).array);
}

/** \fn void reset_double_array(double_array * array)
* \brief Reset the double array to hold nothing.
* \param array Pointer to the dynamic double array.
*/
void reset_double_array(double_array * array)
{
	(*array).size = 0;
}

/** \fn void free_double_array(double_array * array)
 * \brief Free the memory of a dynamic double array.
 * \param array Pointer to the dynamic double array.
 */
void free_double_array(double_array * array)
{
	free((*array).array);
}

void copy_double_array(double_array * from, double_array * to)
{
	int i;
	//to = init_double_array();

	for (i = 0; i < (*from).size; i++)
	{
		add_double(to, (*from).array[i]);
	}
}

/** \fn void sort_double_array(double_array * array)
 * \brief Sort the elements of a dynamic double array with smallest first.
 * \param array Pointer to the dynamic double array.
 */
/*void sort_double_array(double_array array)
{
	int i, j;
	double temp;

	// Using bubble sorts nested loops //
	for(i=0; i<(array.size-1); i++)
	{
		for(j=0; j<(array.size-1)-i; j++)
		{
			// Comparing the values between neighbours //
			if(*(array.array+j+1) < *(array.array+j))
			{
                // Swap neighbours //
                temp = *(array.array+j);
                *(array.array+j) = *(array.array+j+1);
                *(array.array+j+1) = temp;
			}
		}
	}
}*/

/** \fn int quicksort_double(double *array, int elements)
 *  \brief Sorts the elements of the double array in ascending order.
 *  \param Pointer to double array
 *  \param Number of elements that must be sorted
 *  \return integer value indicating success(0) or failure(1)
 */
/*int quicksort_double(double array, int elements)
{
	#define  LEVEL  1000
	double pivot, begin[LEVEL], end[LEVEL];
	int  i=0, left, right ;
	begin[0]=0; end[0]=elements;
	while (i>=0)
	{
		left=begin[i]; right=end[i]-1;
		if (left<right)
		{
			pivot=array[left]; if (i==LEVEL-1) return 1;
			while (left<right)
			{
				while (array[right]>=pivot && left<right) right--;
				if (left<right) array[left++]=array[right];
				while (array[left]<=pivot && left<right) left++;
				if (left<right) array[right--]=array[left];
			}
			array[left]=pivot;
			begin[i+1]=left+1;
			end[i+1]=end[i];
			end[i++]=left;
		}
	    else
	    {
	      i--;
	    }
	}
	return 0;
}*/

/** \fn void add_double(double_array * array, double new_double)
 * \brief Add an double to the dynamic double array.
 * \param array Pointer to the dynamic double array.
 * \param new_double The double to add
 */
void add_double(double_array * array, double new_double)
{
	if((*array).size == (*array).total_size)
	{
		(*array).total_size = (int)((*array).total_size * ARRAY_GROWTH_RATE);
		(*array).array = (double *)realloc((*array).array, ((*array).total_size * sizeof(double)));
	}
	(*array).array[(*array).size] = new_double;
	(*array).size++;
}

/** \fn void remove_double(double_array * array, int index)
 * \brief Remove an double from a dynamic double array.
 * \param array Pointer to the dynamic double array.
 * \param index The index of the double to remove.
 */
void remove_double(double_array * array, int index)
{
	int i;
	if(index < (*array).size)
	{
		/* memcopy?? */
		for(i = index; i < (*array).size - 1; i++)
		{
			(*array).array[i] = (*array).array[i+1];
		}
		(*array).size--;
	}
}

/** \fn void print_double_array(double_array * array)
 * \brief Print the elements of a dynamic double array.
 * \param array Pointer to the dynamic double array.
 */
void print_double_array(double_array * array)
{
	int i;

	for(i=0; i<(*array).size; i++)
	{
		printf("%d> %f", i, (*array).array[i]);
	}
}

/** \fn char_array * init_char_array()
 * \brief Allocate memory for a dynamic char array.
 * \return char_array Pointer to the new dynamic char array.
 */
void init_char_array(char_array * array)
{
	(*array).size = 0;
	(*array).total_size = ARRAY_BLOCK_SIZE;
	(*array).array = (char *)malloc(ARRAY_BLOCK_SIZE * sizeof(char));
	CHECK_POINTER((*array).array);
	(*array).array[0] = '\0';
}

/** \fn void reset_char_array(char_array * array)
* \brief Reset the char array to hold nothing.
* \param array Pointer to the dynamic char array.
*/
void reset_char_array(char_array * array)
{
	(*array).size = 0;
}

/** \fn void free_char_array(char_array * array)
 * \brief Free the memory of a dynamic char array.
 * \param array Pointer to the dynamic char array.
 */
void free_char_array(char_array * array)
{
	free((*array).array);
}

void copy_char_array(char_array * from, char_array * to)
{
	int i;

	for (i = 0; i < (*from).size; i++)
	{
		add_char(to, (*from).array[i]);
	}
}

/** \fn void add_char(char_array * array, char new_char)
 * \brief Add an char to the dynamic char array.
 * \param array Pointer to the dynamic char array.
 * \param new_char The char to add
 */
void add_char(char_array * array, char new_char)
{
	if((*array).size + 1 == (*array).total_size)
	{
		(*array).total_size = (int)((*array).total_size * ARRAY_GROWTH_RATE);
		(*array).array = (char *)realloc((*array).array, ((*array).total_size * sizeof(char)));
	}
	(*array).array[(*array).size] = new_char;
	(*array).array[(*array).size + 1] = '\0';
	(*array).size++;
}

/** \fn void remove_char(char_array * array, int index)
 * \brief Remove an char from a dynamic char array.
 * \param array Pointer to the dynamic char array.
 * \param index The index of the char to remove.
 */
void remove_char(char_array * array, int index)
{
	int i;
	if(index < (*array).size)
	{
		/* memcopy?? */
		for(i = index; i < (*array).size - 1; i++)
		{
			(*array).array[i] = (*array).array[i+1];
		}
		(*array).size--;
	}
}

/** \fn char * copy_array_to_str(char_array * array)
 * \brief Return pointer to string from a char_array.
 * \param array Pointer to the dynamic integer array.
 * \return char Pointer to the new string.
 */
char * copy_array_to_str(char_array * array)
{
	char * new_string = (char *)malloc( ((*array).size + 1) * sizeof(char));
	CHECK_POINTER(new_string);
	return strcpy(new_string, (*array).array);
}

/** \fn void print_char_array(char_array * array)
 * \brief Print the elements of a dynamic char array.
 * \param array Pointer to the dynamic char array.
 */
void print_char_array(char_array * array)
{
	printf("%s", (*array).array);
}


/** \fn int idle()
 * \brief an idle function for use by agents.
 */
int idle()
{
	return 0;
}

int FLAME_get_environment_variable_set_no()
{
	return FLAME_environment_variable_set_no;
}
int FLAME_get_environment_variable_run()
{
	return FLAME_environment_variable_run;
}
double FLAME_get_environment_variable_const_radius()
{
	return FLAME_environment_variable_const_radius;
}
double FLAME_get_environment_variable_const_b()
{
	return FLAME_environment_variable_const_b;
}


