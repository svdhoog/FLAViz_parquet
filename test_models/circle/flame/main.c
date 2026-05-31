/**
 * \file  main.c
 * \brief Holds main function of the program.
 */
#include "header.h"
#include <time.h>

#define FLAME_TIMER_LAYERS 0
#define FLAME_TIMER_IO 0



#define COMPACT_PRINTOUT_P_THRESHOLD 8

/* Set inputpath as global variable */
char inputpath[1000];

/** \fn int main(int argc, char * argv[])
 * \brief Main program loop.
 * \param argc Argument count.
 * \param argv Pointer Pointer to Argument vector.
 */
int main(int argc, char * argv[])
{
	/* Timing variables */
	double start, stop, interval, layer_interval, io_interval;
	FILE *file;
	char data[100];
	char logfilepath[1000];
	char * c;
	int lastd = 0;
	int i;
	int rc;
	int iteration_number = 0;
	int iteration_total;
	int * p_iteration_number = &iteration_number;
	//xmachine_memory_Agent * temp_xmachine_Agent;


	/* Particle cloud data */
	double cloud_data[6] = {0.0,0.0,0.0,0.0,0.0,0.0};
	/* Count to debug function branches */
	int FLAME_debug_count;


/* For partition method. Makes geometric (-g flag) the default but may be overridden with -r for round-robin */
	int partition_method=1;



	/* Output frequency is 1 as default */
	output_frequency = 1;

	/* Set random seed */
	srand((unsigned int) time(NULL));

	srand(0);


	

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
    
	/* For backwards compatabilty allocate current_xmachine */
	current_xmachine = (xmachine *)malloc(sizeof(xmachine));
	if(current_xmachine == NULL) {printf("**** ERROR in Memory check current_xmachine\n");exit(EXIT_FAILURE);}
	/*CHECK_POINTER(current_xmachine);*/

	/* Initialise pointers */
	initialise_pointers();


	printf("FLAME Application: Test Model - Xparser 0.17.1 Circle (x,y)-coordinates \n");


	printf("Debug mode enabled \n");
FLAME_debug_count = 0;
/* Use to stop compiler warnings if not used */
if(FLAME_debug_count == 0) {}




if(argc < 2)
	{

		printf("Usage: %s <number of iterations> [<states_directory>]/<init_state> <partitions> [-f # | -f #+#]\n",argv[0]);
		printf("\t-f\tOutput frequency, 1st # is frequency, 2nd # is the offset if required\n");



		exit(0);
	}
	iteration_total = atoi(argv[1]);
printf("Iterations: %i\n", iteration_total);

	/* Read initial states of x-machines */
	if(argc < 3)
	{
		printf("Need two parameters\n");
		exit(0);
	}
	strcpy(inputpath, argv[2]);
/*printf("Initial states: %s\n", inputpath);*/

	i = 0;
	lastd = -1;
	while(inputpath[i] != '\0')
	{
		/* For windows directories */
		if(inputpath[i] == '\\') lastd=i;
		/* For unix directories */
		if(inputpath[i] == '/') lastd=i;
		i++;
	}
	strcpy(outputpath, inputpath);
	outputpath[lastd+1] = '\0';

/*printf("Ouput dir: %s\n", outputpath);*/


	/* Read number of space partitions (1 by default) */
	totalnodes = 1;
	if(argc > 3)
	{
		totalnodes = atoi(argv[3]);
	}


	i = 3;
	while(argc > i)
	{
		if(strcmp(argv[i],"-f") == 0)
		{
			if(argc > (i+1))
			{
				output_offset = 0;
				/* Find offset, separated by the char '+' */
				c = strchr(argv[(i+1)], '+');
				if(c == NULL)
				{
					output_frequency = atoi(argv[(i+1)]);
					printf("Using output frequency of: %d\n", output_frequency);
				}
				else
				{
					output_offset = atoi(argv[(i+1)]+(c-argv[(i+1)])+1);
					argv[(i+1)][c-argv[(i+1)]] = '\0';
					output_frequency = atoi(argv[(i+1)]);
					printf("Using output frequency of: %d with offset %d\n", output_frequency, output_offset);
				}

				if(output_frequency == 0)
				{
					printf("Output frequency cannot be zero\n");
					exit(0);
				}

				i++;
			}
			else
			{
				printf("Output frequency number not defined\n");
				exit(0);
			}
		}
		/* Partitioning method: -g = geometric, -r = round-robin */
		if(strcmp(argv[i],"-g") == 0) partition_method = 1;
		if(strcmp(argv[i],"-r") == 0) partition_method = 2;
		i++;
	}


	    /* Read initial data into p_xmachine  */

       //agent_list = p_xmachine;
       readinitialstates(inputpath, outputpath, p_iteration_number, cloud_data, partition_method, 0);
       /* Generate partitions */
       generate_partitions(cloud_data,totalnodes,partition_method);
       save_partition_data();





    /* Partition data */
    /* stc: no partitions in serial */
	//partition_data(totalnodes, agent_list, cloud_data, partition_method);





/* Use MB_IndexMap routines from libmboard v0.2 */
/* For each agent constant (that is used in a filter(?))
 * declare an index map handle */



		/*i = 0;
		current_node = *p_node_info;
		while(current_node)
		{
			printf("No of agents on partition %d: %d\n", current_node->node_id, current_node->agent_total);
			i += current_node->agent_total;
			current_node = current_node->next;
		}
		printf("Agent total check: %d\n", i);*/

        /* restore current_node pointer */
		//current_node = *p_node_info;



	/* Start log file (now so that xvisualiser can read straight away) */

	/* Write log file */
	// Check if outputpath leaves enough room for "log.xml" (7 bytes) + null terminator (1 byte)
	if (strlen(outputpath) + 8 > sizeof(logfilepath)) {
	    fprintf(stderr, "Error: outputpath is too long for the log file path buffer.\n");
	    // Handle the error gracefully (e.g., return, exit, or fall back)
	    exit(0); 
	}
	// GCC now knows this snprintf will never truncate, still we use pragma's to shut up the compiler
	#pragma GCC diagnostic push
	#pragma GCC diagnostic ignored "-Wformat-truncation"
	snprintf(logfilepath, sizeof(logfilepath), "%slog.xml", outputpath); /* use snprintf to protect against overflow */
	#pragma GCC diagnostic pop
	if((file = fopen(logfilepath, "w"))==NULL)
	{
		printf("Error: cannot open file '%s' for writing\n", logfilepath);
		exit(0);
	}

	(void)fputs("<model_run>\n", file);
	(void)fputs("<codetype>", file);
	(void)fputs("serial", file);

	(void)fputs("</codetype>\n", file);
	(void)fputs("<nodes>", file);
	sprintf(data, "%i", totalnodes);
	(void)fputs(data, file);
	(void)fputs("</nodes>\n", file);

	/* print timer into */
	(void)fputs("<!-- <time> unit: milliseconds -->\n", file);

	sprintf(data, "unspecified");
	
	(void)fputs("<!-- <time> timer resolution: ", file);
	(void)fputs(data, file);
	(void)fputs(")-->\n", file);

	start = get_time();
	stop = get_time();
	sprintf(data, "%.2e ms", (stop - start) * 1000.0);
	(void)fputs("<!-- <time> timer overhead: ~", file);
	(void)fputs(data, file);
	(void)fputs(")-->\n", file);


	(void)fclose(file);


	/* For each message check if their exists agents that input/output the message */
	

#ifdef START_END	
/* Call initialisation function */
	start_simulation();
#endif

/* Start timing */
	start = get_time();

	for(iteration_loop=iteration_number+1; iteration_loop < iteration_number+iteration_total+1; iteration_loop++)
	{
#ifdef START_END
/* Start iteration function */
	start_iteration();
#endif
		interval = get_time(); 		 /* Start timer for iteration */
		
		if(FLAME_TIMER_LAYERS)
		{
			layer_interval = get_time(); /* Start timer for layer 1 */
		}
		
		/* Print out iteration number */
		
		fprintf(stdout, "Iteration - %d\n", iteration_loop);
		(void)fflush(stdout);
        
		/* START OF ITERATION */
		
		/* For each message check if their exists agents that input/output the message */
        
        
		
		


	if(FLAME_TEST_PRINT_START_AND_END_OF_MODEL_FUNCTIONS) printf("start set_xy\n");
	current_xmachine_Agent_holder = Agent_start_Agent_state->agents;
	while(current_xmachine_Agent_holder)
	{
		temp_xmachine_Agent_holder = current_xmachine_Agent_holder->next;
		current_xmachine_Agent = current_xmachine_Agent_holder->agent;
		current_xmachine_Agent_next_state = Agent_end_Agent_state;
		/* For backwards compatibility set current_xmachine */
		current_xmachine->xmachine_Agent = NULL;
		current_xmachine->xmachine_Agent = current_xmachine_Agent;

		

		

			i = set_xy();

		

			if(i == 1)
			{
				free_Agent_agent(current_xmachine_Agent_holder, Agent_start_Agent_state);
			}
			else
			{
				transition_Agent_agent(current_xmachine_Agent_holder, Agent_start_Agent_state, Agent_end_Agent_state);
			}
		

		current_xmachine_Agent = NULL;

		current_xmachine_Agent_holder = temp_xmachine_Agent_holder;
	}
	if(FLAME_TEST_PRINT_START_AND_END_OF_MODEL_FUNCTIONS) printf("finish set_xy\n");


if(FLAME_TIMER_LAYERS)
{
	/* Save layer time to log file (log.xml)*/
	if((file = fopen(logfilepath, "a"))==NULL)
	{
		printf("Error: cannot open file '%s' for writing\n", logfilepath);
		exit(0);
	}
	(void)fputs("    <layer><no>", file);
	sprintf(data, "%i", 0);
	(void)fputs(data, file);
	(void)fputs("</no><time>", file);
	sprintf(data, "%d", (int)((get_time() - layer_interval) * 1000) );
	(void)fputs(data, file);
	(void)fputs("</time></layer>\n", file);
	(void)fclose(file);
	/* End of layer number 0 */

	layer_interval = get_time(); /* Start timer for next layer */
}
/* Start of next layer */
/* Clear message boards that have finished being used
 * and sync complete if doing late sync complete */


/*	if(iteration_loop%output_frequency == output_offset)
	{
		//XML output
		saveiterationdata(iteration_loop); 
		
		//Parquet output
		saveiterationdata_parquet(iteration_loop);
	}
*/

	/*printf("Agent_end_Agent_state->count = %d\n", Agent_end_Agent_state->count);*/
	Agent_end_Agent_state->count = 0;

	/*printf("Agent_start_Agent_state->count = %d\n", Agent_start_Agent_state->count);*/
	Agent_start_Agent_state->count = 0;

	/* Move agents to their start states */

	current_xmachine_Agent_holder = Agent_end_Agent_state->agents;
	while(current_xmachine_Agent_holder)
	{
		temp_xmachine_Agent_holder = current_xmachine_Agent_holder->next;
		transition_Agent_agent(current_xmachine_Agent_holder, Agent_end_Agent_state, Agent_start_Agent_state);

		current_xmachine_Agent_holder = temp_xmachine_Agent_holder;
	}

    if(iteration_loop%output_frequency == output_offset)
    {
		if(FLAME_TIMER_IO)
		{
	        /* Start timer for disk I/O */
			io_interval = get_time();
		}

		//XML output
		saveiterationdata(iteration_loop); 
		
		//Parquet output
		saveiterationdata_parquet(iteration_loop);

		if(FLAME_TIMER_IO)
		{
			/* Save I/O time to log file */
			if((file = fopen(logfilepath, "a"))==NULL)
			{
				printf("Error: cannot open file '%s' for writing\n", logfilepath);
				exit(0);
			}
			(void)fputs("<disk_io>", file);
			(void)fputs("<time>", file);
			sprintf(data, "%03d", (int)((get_time() - io_interval) * 1000) );
			(void)fputs(data, file);
			(void)fputs("</time></disk_io>\n", file);
			(void)fclose(file);
		}
    }

	/* Calculate if any agents need to jump S.P. */
	/* propagate_agents(); */
	
	/* Save iteration time to log file */
	if((file = fopen(logfilepath, "a"))==NULL)
	{
		printf("Error: cannot open file '%s' for writing\n", logfilepath);
		exit(0);
	}
	(void)fputs("<iteration><no>", file);
	sprintf(data, "%i", iteration_loop);
	(void)fputs(data, file);
	(void)fputs("</no><time>", file);
	sprintf(data, "%d", (int)((get_time() - interval) * 1000) );
	(void)fputs(data, file);
	(void)fputs("</time></iteration>\n", file);
	(void)fclose(file);

#ifdef START_END
/* End iteration function */
	end_iteration();
#endif
	}

#ifdef START_END
/* End simulation function */
	end_simulation();
#endif

    



	/* Stop timing and print total time */
	stop = get_time();
	total_time = stop - start;
	printf("Execution time - %d:%02d:%03d [mins:secs:msecs]\n",
       (int)(total_time/60), ((int)total_time)%60, (((int)(total_time * 1000.0)) % 1000));

	clean_up(0);

	/* Exit successfully by returning zero to Operating System */
	return 0;
}
