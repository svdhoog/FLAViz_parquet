/**
 * \file  xml.c
 * \brief Holds xml reading and writing functions.
 */

#include "header.h"

#define CONST_BUFFER_SIZE 1000000

/** \fn void read_int_static_array(char * buffer, int * j, int ** int_static_array)
 * \brief Reads integer static array.
 */
int read_int_static_array(char * buffer, int /*@unused@*/ buffer_size, int * j, int * int_static_array, int /*@unused@*/ size)
{
	int arraycount = 0;
	int array_k;
	char arraydata[CONST_BUFFER_SIZE];
	
	while(buffer[(*j)] != '{')
	{
		if(buffer[(*j)] != ' ') return -1;
		else if(buffer[(*j)] == '\0') return -1;
		else (*j)++;
	}
	(*j)++;

	while(buffer[(*j)] != '}')
	{
		array_k = 0;
		while(buffer[(*j)] != ',' && buffer[(*j)] != '}')
		{
			if(buffer[(*j)] == '\0') return -1;
			arraydata[array_k] = buffer[(*j)];
			array_k++;
			(*j)++;
		}
		arraydata[array_k] = '\0';
		if (arraycount < size) int_static_array[arraycount] = atoi(arraydata);
		arraycount++;
		if(buffer[(*j)] != '}') (*j)++;
	}

	if (arraycount > size)
	{
				fprintf(stderr, "WARNING: %d 'int' values provided for static array of size %d. Surplus values ignored.\n",
				arraycount, size);
	}
	
	(*j)++;
	return 0;
}

/** \fn void read_float_static_array(char * buffer, int * (*j), int ** float_static_array)
 * \brief Reads float static array.
 */
int read_float_static_array(char * buffer, int /*@unused@*/ buffer_size, int * j, float * float_static_array, int /*@unused@*/ size)
{
	int arraycount = 0;
	int array_k;
	char arraydata[CONST_BUFFER_SIZE];

	while(buffer[(*j)] != '{')
	{
		if(buffer[(*j)] != ' ') return -1;
		else if(buffer[(*j)] == '\0') return -1;
		else (*j)++;
	}
	(*j)++;

	while(buffer[(*j)] != '}')
	{
		array_k = 0;
		while(buffer[(*j)] != ',' && buffer[(*j)] != '}')
		{
			if(buffer[(*j)] == '\0') return -1;
			arraydata[array_k] = buffer[(*j)];
			array_k++;
			(*j)++;
		}
		arraydata[array_k] = '\0';
		if (arraycount < size) float_static_array[arraycount] = (float)atof(arraydata);
		arraycount++;
		if(buffer[(*j)] != '}') (*j)++;
	}
	
	if (arraycount > size)
	{
				fprintf(stderr, "WARNING: %d 'float' values provided for static array of size %d. Surplus values ignored.\n",
				arraycount, size);
	}
	
	(*j)++;
	return 0;
}

/** \fn void read_double_static_array(char * buffer, int * (*j), int ** double_static_array)
 * \brief Reads double static array.
 */
int read_double_static_array(char * buffer, int /*@unused@*/ buffer_size, int * j, double * double_static_array, int /*@unused@*/ size)
{
	int arraycount = 0;
	int array_k;
	char arraydata[CONST_BUFFER_SIZE];

	while(buffer[(*j)] != '{')
	{
		if(buffer[(*j)] != ' ') return -1;
		else if(buffer[(*j)] == '\0') return -1;
		else (*j)++;
	}
	(*j)++;

	while(buffer[(*j)] != '}')
	{
		array_k = 0;
		while(buffer[(*j)] != ',' && buffer[(*j)] != '}')
		{
			if(buffer[(*j)] == '\0') return -1;
			arraydata[array_k] = buffer[(*j)];
			array_k++;
			(*j)++;
		}
		arraydata[array_k] = '\0';
		if (arraycount < size) double_static_array[arraycount] = atof(arraydata);		
		arraycount++;
		if(buffer[(*j)] != '}') (*j)++;
	}

	if (arraycount > size)
	{
		fprintf(stderr, "WARNING: %d 'double' values provided for static array of size %d. Surplus values ignored.\n",
				arraycount, size);
	}
	
	(*j)++;
	return 0;
}

/** \fn void read_char_static_array(char * buffer, int * (*j), int ** char_static_array)
 * \brief Reads char static array.
 */
int read_char_static_array(char * buffer, int /*@unused@*/ buffer_size, int * j, char * char_static_array, int size)
{
	int arraycount;
	
	while(buffer[(*j)] == ' ')
	{
		(*j)++;
	}
	
	for(arraycount = 0; arraycount < size; arraycount++)
	{
		char_static_array[arraycount] = buffer[(*j)];
		(*j)++;
	}

	//(*j)++;
	return 0;
}

/** \fn void read_int_dynamic_array(char * buffer, int * (*j), int ** int_dynamic_array)
 * \brief Reads integer dynamic array.
 */
int read_int_dynamic_array(char * buffer, int /*@unused@*/ buffer_size, int * j, int_array * int_dynamic_array)
{
	int arraycount = 0;
	int array_k;
	char arraydata[CONST_BUFFER_SIZE];

	while(buffer[(*j)] != '{')
	{
		if(buffer[(*j)] != ' ') return -1;
		else if(buffer[(*j)] == '\0') return -1;
		else (*j)++;
	}
	(*j)++;

	while(buffer[(*j)] != '}')
	{
		array_k = 0;
		while(buffer[(*j)] != ',' && buffer[(*j)] != '}')
		{
			if(buffer[(*j)] == '\0') return -1;
			arraydata[array_k] = buffer[(*j)];
			array_k++;
			(*j)++;
		}
		arraydata[array_k] = '\0';
		add_int(int_dynamic_array, atoi(arraydata));
		arraycount++;
		if(buffer[(*j)] != '}') (*j)++;
	}

	(*j)++;
	return 0;
}

/** \fn void read_float_dynamic_array(char * buffer, int * (*j), int ** float_dynamic_array)
 * \brief Reads float dynamic array.
 */
int read_float_dynamic_array(char * buffer, int /*@unused@*/ buffer_size, int * j, float_array * float_dynamic_array)
{
	int arraycount = 0;
	int array_k;
	char arraydata[CONST_BUFFER_SIZE];

	while(buffer[(*j)] != '{')
	{
		if(buffer[(*j)] != ' ') return -1;
		else if(buffer[(*j)] == '\0') return -1;
		else (*j)++;
	}
	(*j)++;

	while(buffer[(*j)] != '}')
	{
		array_k = 0;
		while(buffer[(*j)] != ',' && buffer[(*j)] != '}')
		{
			if(buffer[(*j)] == '\0') return -1;
			arraydata[array_k] = buffer[(*j)];
			array_k++;
			(*j)++;
		}
		arraydata[array_k] = '\0';
		add_float(float_dynamic_array, (float)atof(arraydata));
		arraycount++;
		if(buffer[(*j)] != '}') (*j)++;
	}

	(*j)++;
	return 0;
}

/** \fn void read_double_dynamic_array(char * buffer, int * (*j), int ** double_dynamic_array)
 * \brief Reads double dynamic array.
 */
int read_double_dynamic_array(char * buffer, int /*@unused@*/ buffer_size, int * j, double_array * double_dynamic_array)
{
	int arraycount = 0;
	int array_k;
	char arraydata[CONST_BUFFER_SIZE];

	while(buffer[(*j)] != '{')
	{
		if(buffer[(*j)] != ' ') return -1;
		else if(buffer[(*j)] == '\0') return -1;
		else (*j)++;
	}
	(*j)++;

	while(buffer[(*j)] != '}')
	{
		array_k = 0;
		while(buffer[(*j)] != ',' && buffer[(*j)] != '}')
		{
			if(buffer[(*j)] == '\0') return -1;
			arraydata[array_k] = buffer[(*j)];
			array_k++;
			(*j)++;
		}
		arraydata[array_k] = '\0';
		add_double(double_dynamic_array, atof(arraydata));
		arraycount++;
		if(buffer[(*j)] != '}') (*j)++;
	}

	(*j)++;
	return 0;
}

/** \fn void read_char_dynamic_array(char * buffer, int * (*j), int ** char_dynamic_array)
 * \brief Reads char dynamic array.
 */
int read_char_dynamic_array(char * buffer, int /*@unused@*/ buffer_size, int * j, char_array * char_dynamic_array)
{
	if(*j > buffer_size) return -1;
	
	while(buffer[(*j)] == ' ')
	{
		(*j)++;
	}
	
	while(buffer[(*j)] != '\0' && buffer[(*j)] != ',' && buffer[(*j)] != '}')
	{
		add_char(char_dynamic_array, buffer[(*j)]);
		(*j)++;
	}
	
	return 0;
}




int readEnvironmentXML(char * location)
{
	FILE * file;
	char c = '\0';
	char buffer[CONST_BUFFER_SIZE];
	int index = 0;
	int in_environment = 0;
	int in_set_no = 0;
	int in_run = 0;
	int in_const_radius = 0;
	int in_const_b = 0;
	

	buffer[0] = '\0';

	/* Open file */
	if((file = fopen(location, "r"))==NULL)
	{
		printf("Error: cannot open import xml file '%s'\n", location);
		exit(0);
	}
	printf("Reading environment data from: %s\n", location);
	/* Keep reading file until EOF */
	while(c != (char)EOF)
	{
		/* Get the next char from the file */
		c = (char)fgetc(file);
		if(c == '>')
		{
			buffer[index] = '\0';
			if(strcmp(buffer, "environment") == 0) in_environment = 1;
			if(strcmp(buffer, "/environment") == 0) in_environment = 0;
			if(strcmp(buffer, "set_no") == 0) in_set_no = 1;
			if(strcmp(buffer, "/set_no") == 0) in_set_no = 0;
			if(strcmp(buffer, "run") == 0) in_run = 1;
			if(strcmp(buffer, "/run") == 0) in_run = 0;
			if(strcmp(buffer, "const_radius") == 0) in_const_radius = 1;
			if(strcmp(buffer, "/const_radius") == 0) in_const_radius = 0;
			if(strcmp(buffer, "const_b") == 0) in_const_b = 1;
			if(strcmp(buffer, "/const_b") == 0) in_const_b = 0;
			
			index = 0;
			buffer[index] = '\0';
		}
		else if(c == '<')
		{
			buffer[index] = '\0';
			if(in_environment == 1)
			{
				if(in_set_no == 1) { FLAME_environment_variable_set_no = atoi(buffer); }
				if(in_run == 1) { FLAME_environment_variable_run = atoi(buffer); }
				if(in_const_radius == 1) { FLAME_environment_variable_const_radius = atof(buffer); }
				if(in_const_b == 1) { FLAME_environment_variable_const_b = atof(buffer); }
				
			}
			index = 0;
			buffer[index] = '\0';
		}
		else
		{
			buffer[index] = c;
			if(index < CONST_BUFFER_SIZE-1) index++;
            else
            {
                printf("Error: environment reading buffer too small\n");
                printf("%s\n", buffer);
                exit(0);
            }            
		}
	}
	/* Close file */
	(void)fclose(file);

	return 0;
}

int readAgentXML(char * location,
				double cloud_data[],
				int partition_method,
				int flag,
				int number_partitions,
				int agent_count,
				int * itno)
{
	FILE * file;
	char c = '\0';
	char buffer[CONST_BUFFER_SIZE];
	char agentname[10000];
	int index = 0;
	int j; /* Index for reading arrays */
	int rc;
	int in_itno = 0;
	int FLAME_in_xagent = 0;
	int FLAME_in_name = 0;
	int in_Agent_agent = 0;
	
	int in_id = 0;
	int in_x = 0;
	int in_y = 0;
	int in_a = 0;
	int in_b = 0;
	
	xmachine_memory_Agent * current_Agent_agent = NULL;
	
	/* Things for round-robin partitioning */
	int geometric = 1;
	int other = 2;
	double posx=0.0, posy=0.0, posz=0.0;

	j = 0;
	rc = 0;
	
	/* Use j and rc to stop compiler warnings if not used */
	if(j == 0 && rc == 0) {}
	
	agentname[0] = '\0';
	buffer[0] = '\0';

	/* Open file */
	if((file = fopen(location, "r"))==NULL)
	{
		printf("Error: cannot open import xml file '%s'\n", location);
		exit(0);
	}
	printf("Reading agent data from: %s\n", location);
	/* Keep reading file until EOF */
	while(c != (char)EOF)
	{
		/* Get the next char from the file */
		c = (char)fgetc(file);
		if(c == '>')
		{
			buffer[index] = '\0';
			if(strcmp(buffer, "itno") == 0) in_itno = 1;
			if(strcmp(buffer, "/itno") == 0) in_itno = 0;
			if(strcmp(buffer, "xagent") == 0)
			{
				FLAME_in_xagent = 1;
				agentname[0] = '\0';
			}
			if(strcmp(buffer, "/xagent") == 0)
			{	
				if(strcmp(agentname, "Agent") == 0)
				{
					if(current_Agent_agent == NULL) { printf("Memory error reading Agent agent\n"); exit(0); }
					
					posx = (double)current_Agent_agent->x;
					posy = (double)current_Agent_agent->y;
					posz = (double)0.0;
					
					/* If flag is zero just read the data. We'll partition later.
					 * If flag is not zero we aleady have partition data so can read and distribute to the current node.*/
					if( flag == 0 )
					{
						/* Next line should be commented out? */
						add_Agent_agent_internal(current_Agent_agent, Agent_start_Agent_state);

						/* Update the cloud data */
						if ( posx < cloud_data[0] ) cloud_data[0] = posx;
						if ( posx > cloud_data[1] ) cloud_data[1] = posx;
						if ( posy < cloud_data[2] ) cloud_data[2] = posy;
						if ( posy > cloud_data[3] ) cloud_data[3] = posy;
						if ( posz < cloud_data[2] ) cloud_data[4] = posz;
						if ( posz > cloud_data[3] ) cloud_data[5] = posz;
					}
					else
					{
						if(partition_method == geometric)
						{
							if (
								((current_node->partition_data[0] == SPINF) || (current_node->partition_data[0] != SPINF && posx >= current_node->partition_data[0])) &&
								((current_node->partition_data[1] == SPINF) || (current_node->partition_data[1] != SPINF && posx < current_node->partition_data[1])) &&
								((current_node->partition_data[2] == SPINF) || (current_node->partition_data[2] != SPINF && posy >= current_node->partition_data[2])) &&
								((current_node->partition_data[3] == SPINF) || (current_node->partition_data[3] != SPINF && posy < current_node->partition_data[3])) &&
								((current_node->partition_data[4] == SPINF) || (current_node->partition_data[4] != SPINF && posz >= current_node->partition_data[4])) &&
								((current_node->partition_data[5] == SPINF) || (current_node->partition_data[5] != SPINF && posz < current_node->partition_data[5]))
							)
							{
								add_Agent_agent_internal(current_Agent_agent, Agent_start_Agent_state);
							}
						}
						else if (partition_method == other)
						{
							if (agent_count % number_partitions == 0)
							{
								add_Agent_agent_internal(current_Agent_agent, Agent_start_Agent_state);
							}
							++agent_count;
						}
					}
				}
				else
				{
					printf("Warning: agent name undefined - '%s'\n", agentname);
					exit(0);
				}
				agentname[0] = '\0';
				FLAME_in_xagent = 0;
				in_Agent_agent = 0;
				
			}
			if(strcmp(buffer, "name") == 0) FLAME_in_name = 1;
			if(strcmp(buffer, "/name") == 0) FLAME_in_name = 0;
			if(strcmp(buffer, "id") == 0) { in_id = 1; }
			if(strcmp(buffer, "/id") == 0) { in_id = 0; }
			if(strcmp(buffer, "x") == 0) { in_x = 1; }
			if(strcmp(buffer, "/x") == 0) { in_x = 0; }
			if(strcmp(buffer, "y") == 0) { in_y = 1; }
			if(strcmp(buffer, "/y") == 0) { in_y = 0; }
			if(strcmp(buffer, "a") == 0) { in_a = 1; }
			if(strcmp(buffer, "/a") == 0) { in_a = 0; }
			if(strcmp(buffer, "b") == 0) { in_b = 1; }
			if(strcmp(buffer, "/b") == 0) { in_b = 0; }
			
			index = 0;
			buffer[index] = '\0';
		}
		else if(c == '<')
		{
			buffer[index] = '\0';
			
			if(in_itno && FLAME_in_xagent == 0) *itno = atoi(buffer);
			if(FLAME_in_xagent == 1)
			{
				if(FLAME_in_name == 1)
				{
					strcpy(agentname, buffer);

					if(strcmp(agentname, "Agent") == 0)
					{
						current_Agent_agent = init_Agent_agent();
						in_Agent_agent = 1;
					}
					else
					{
						printf("Warning: agent name undefined - '%s'\n", agentname);
						exit(0);
					}
				}
				else if(in_Agent_agent == 1)
				{
					if(in_id) { current_Agent_agent->id = atoi(buffer); }
					if(in_x) { current_Agent_agent->x = atof(buffer); }
					if(in_y) { current_Agent_agent->y = atof(buffer); }
					if(in_a) { current_Agent_agent->a = atof(buffer); }
					if(in_b) { current_Agent_agent->b = atof(buffer); }
				 }
			}
			index = 0;
			buffer[index] = '\0';
		}
		else
		{
			buffer[index] = c;
            if(index < CONST_BUFFER_SIZE-1) index++;
			else
			{
                printf("Error: agent reading buffer too small\nAt index: %d Buffer size: %d", index, CONST_BUFFER_SIZE);
				printf("%s\n", buffer);
				exit(0);
			}
		}
	}
	/* Close file */
	(void)fclose(file);

	return 0;
}

/** \fn void check_location_exists(char * location)
 * \brief Check that a directory exists.
 * \param location The directory location to check.
 */
int check_location_exists(char * location)
{
	/* Save a dummy file to directory and remove.
	 * This checks directory exists and is writable */
	FILE * file;
	char * buffer;

	buffer = (char *)malloc( (strlen(location) + strlen("dummy.temp") + 1) * sizeof(char));
	strcpy(buffer, location);
	strcat(buffer, "dummy.temp");

	if((file = fopen(buffer, "w")) == NULL) return 0;

	(void)fclose(file);
	/* Remove dummy file */
	remove(buffer);

	return 1;
}


/** \fn void readinitialstates(char * filename, int * itno, xmachine ** agent_list, double cloud_data[6], int flag)
 * \brief Read initial X-machine memory starting values from a file.
 * \param filename The path to the file.
 * \param filelocation The directory of the location
 * \param itno Pointer to the iteration number.
 * \param agent_list List of agents in the model to be constructed by this function.
 * \param cloud_data Max and min x,y,z coordinates of agents.
 * \param partition_method Identifies partitioning method: 1 = geometric, 2 = round-robin
 * \param flag Flag for whether to check space partitions.
 */
void readinitialstates(char * filename, char * filelocation, int * itno, double cloud_data[],
					   int partition_method, int flag)
{
	/* Pointer to file */
	FILE *file;
	/* Char and char buffer for reading file to */
	char c = '\0';
	char buffer[CONST_BUFFER_SIZE];
	char FLAME_location[10000];
	char FLAME_format[10000];
	char FLAME_type[10000];
	FLAME_output * current_FLAME_output = NULL;

	/* Things for round-robin partitioning */
	int agent_count = 0;
	int number_partitions = 0;
	int geometric=1;
	int other=2;
	

	/* Cloud data array initialisation */
	# ifndef S_SPLINT_S
	cloud_data[0] = SPINF;
	cloud_data[1] = -SPINF;
	cloud_data[2] = SPINF;
	cloud_data[3] = -SPINF;
	cloud_data[4] = SPINF;
	cloud_data[5] = -SPINF;
	# endif

	/* Temporary node and head of associated agent list to allow adding agents */
	node_information temp_node;

	/* Pointer to x-memory for initial state data */
	/*xmachine * current_xmachine;*/
	/* Variables for checking tags */
	int reading = 1;
	int i = 0;
	int rc;
	int in_tag = 0;
	int in_itno = 0;
	int FLAME_in_imports = 0;
	int FLAME_in_import = 0;
	int FLAME_in_outputs = 0;
	int FLAME_in_output = 0;
	int FLAME_in_location = 0;
	int FLAME_in_format = 0;
	int FLAME_in_type = 0;
	int FLAME_in_time = 0;
	int FLAME_in_period = 0;
	int FLAME_in_phase = 0;
	int FLAME_in_name = 0;

	/* Initialise environment vars */
	FLAME_environment_variable_set_no = 0;
	FLAME_environment_variable_run = 0;
	FLAME_environment_variable_const_radius = 0.0;
	FLAME_environment_variable_const_b = 0.0;
	

	/* Open config file to read-only */
	if((file = fopen(filename, "r"))==NULL)
	{
		printf("Error: opening initial states '%s'\n", filename);
		exit(0);
	}
	
	/* Initialise variables */
    *itno = 0;





	if(partition_method==geometric) printf("xml: Geometric partitioning\n");
	else if(partition_method==other) printf("xml: Round-robin partitioning\n");
	else printf("xml: Error - invalid partitioning method\n");


	/* Set p_xmachine to the agent list passed in then new agents are added to this list
	 * Will be set to agent list for specific node is space partitions are already known (flag=1)
	 */
	/* If we're reading without knowing partitions already then use the dummy current node (it's not in the list of nodes)*/
	if (flag == 0) current_node = &temp_node;

	printf("Reading initial data file: %s\n", filename);
	/* Read file until end of xml */
	while(reading==1)
	{
		/* Get the next char from the file */
		c = (char)fgetc(file);

		/* If the end of a tag */
		if(c == '>')
		{
			/* Place 0 at end of buffer to make chars a string */
			buffer[i] = 0;

			if(strcmp(buffer, "states") == 0) reading = 1;
			if(strcmp(buffer, "/states") == 0) reading = 0;
			if(strcmp(buffer, "itno") == 0) in_itno = 1;
			if(strcmp(buffer, "/itno") == 0) in_itno = 0;
			if(strcmp(buffer, "imports") == 0) FLAME_in_imports = 1;
			if(strcmp(buffer, "/imports") == 0) FLAME_in_imports = 0;
			if(strcmp(buffer, "import") == 0)
			{
				/*FLAME_location[0] = '\0';*/
				strcpy(FLAME_location, filelocation);
				FLAME_format[0] = '\0';
				FLAME_type[0] = '\0';

				FLAME_in_import = 1;
			}
			if(strcmp(buffer, "/import") == 0)
			{
				if(strcmp("agent", FLAME_type) == 0 || strcmp("environment", FLAME_type) == 0)
				{
					if(strcmp("xml", FLAME_format) == 0)
					{
						if(strcmp("agent", FLAME_type) == 0) readAgentXML(FLAME_location, cloud_data, partition_method, flag, number_partitions, agent_count, itno);
						if(strcmp("environment", FLAME_type) == 0) readEnvironmentXML(FLAME_location);
					}
					else
					{
						printf("Error: import format '%s' is unsupported\n", FLAME_format);
						exit(0);
					}
				}
				else
				{
					printf("Error: import type '%s' is not agent or environment\n", FLAME_type);
					exit(0);
				}

				FLAME_in_import = 0;
			}
			if(strcmp(buffer, "location") == 0) FLAME_in_location = 1;
			if(strcmp(buffer, "/location") == 0) FLAME_in_location = 0;
			if(strcmp(buffer, "format") == 0) FLAME_in_format = 1;
			if(strcmp(buffer, "/format") == 0) FLAME_in_format = 0;
			if(strcmp(buffer, "type") == 0) FLAME_in_type = 1;
			if(strcmp(buffer, "/type") == 0) FLAME_in_type = 0;
			if(strcmp(buffer, "outputs") == 0) FLAME_in_outputs = 1;
			if(strcmp(buffer, "/outputs") == 0) FLAME_in_outputs = 0;
			if(strcmp(buffer, "output") == 0)
			{
				if(FLAME_in_outputs == 1)
				{
					current_FLAME_output = add_FLAME_output(&FLAME_outputs);
	
					FLAME_in_output = 1;
				}
			}
			if(strcmp(buffer, "/output") == 0)
			{
				if(FLAME_in_outputs == 1)
				{
					if(current_FLAME_output->type == -1)
					{
						printf("Error: an output type has not been set\n");
						exit(0);
					}
					if(current_FLAME_output->format == -1)
					{
						printf("Error: an output format has not been set\n");
						exit(0);
					}
					if(current_FLAME_output->location == NULL)
					{
						printf("Error: an output location has not been set\n");
						exit(0);
					}
					/* If type is xml check if location exists */
					if(current_FLAME_output->type == 0)
					{
						rc = check_location_exists(current_FLAME_output->location);
						if(rc == 0)
						{
							printf("Error: location directory '%s' does not exist\n", current_FLAME_output->location);
							exit(0);
						}
					}
					/* Period has to be larger than 0 */
					if(current_FLAME_output->period < 1)
					{
						printf("Error: output period is less than 1: '%d'\n", current_FLAME_output->period);
						exit(0);
					}
					/* Phase cannot be equal or larger than period */
					if(current_FLAME_output->phase >= current_FLAME_output->period)
					{
						printf("Error: output phase is more or equal to period: '%d'\n", current_FLAME_output->phase);
						exit(0);
					}
	
					FLAME_in_output = 0;
				}
			}
			if(strcmp(buffer, "time") == 0) FLAME_in_time = 1;
			if(strcmp(buffer, "/time") == 0) FLAME_in_time = 0;
			if(strcmp(buffer, "period") == 0) FLAME_in_period = 1;
			if(strcmp(buffer, "/period") == 0) FLAME_in_period = 0;
			if(strcmp(buffer, "phase") == 0) FLAME_in_phase = 1;
			if(strcmp(buffer, "/phase") == 0) FLAME_in_phase = 0;
			if(strcmp(buffer, "name") == 0) FLAME_in_name = 1;
			if(strcmp(buffer, "/name") == 0) FLAME_in_name = 0;

			/* End of tag and reset buffer */
			in_tag = 0;
			i = 0;
		}
		/* If start of tag */
		else if(c == '<')
		{
			/* Place /0 at end of buffer to end numbers */
			buffer[i] = 0;
			/* Flag in tag */
			in_tag = 1;

			if(in_itno) *itno = atoi(buffer);
			if(FLAME_in_imports == 1)
			{
				if(FLAME_in_import == 1)
				{
					if(FLAME_in_location == 1) strcat(FLAME_location, buffer);
					if(FLAME_in_format == 1) strcpy(FLAME_format, buffer);
					if(FLAME_in_type == 1) strcpy(FLAME_type, buffer);
				}
			}
			if(FLAME_in_outputs == 1)
			{
				if(FLAME_in_output == 1)
				{
					if(FLAME_in_type == 1)
					{
						if(strcmp("snapshot", buffer) == 0) current_FLAME_output->type = 0;
						else if(strcmp("agent", buffer) != 0)
						{
							printf("Error: output type is not 'snapshot' or an 'agent': '%s'\n", buffer);
							exit(0);
						}
					}
					if(FLAME_in_name == 1)
					{
						if(strcmp("Agent", buffer) == 0) current_FLAME_output->type = 1;
						else 
						{
							printf("Error: output name is not an agent name: '%s'\n", buffer);
							exit(0);
						}
					}
					if(FLAME_in_format == 1)
					{
						if(strcmp("xml", buffer) == 0) current_FLAME_output->format = 0;
						else
						{
							printf("Error: output format is unsupported: '%s'\n", buffer);
							exit(0);
						}
					}
					if(FLAME_in_location == 1)
					{
						current_FLAME_output->location = (char *)malloc( (strlen(filelocation) + strlen(buffer) + 1) * sizeof(char));
						strcpy(current_FLAME_output->location, filelocation);
						strcat(current_FLAME_output->location, buffer);
					}
					if(FLAME_in_time == 1)
					{
						if(FLAME_in_period == 1) current_FLAME_output->period = atoi(buffer);
						if(FLAME_in_phase == 1)  current_FLAME_output->phase = atoi(buffer);
					}
				}
			}
			/* Reset buffer */
			i = 0;
		}
		/* If in tag put read char into buffer */
		else if(in_tag == 1)
		{
			buffer[i] = c;
			i++;
		}
		/* If in data read char into buffer */
		else
		{
			buffer[i] = c;
			i++;
		}
	}

	/* Close the file */
	(void)fclose(file);

	/* Also try and read environment and agents from 0.xml */
	readEnvironmentXML(filename);
	readAgentXML(filename, cloud_data, partition_method, flag, number_partitions, agent_count, itno);

	/* If outputs is empty add default snapshot for every iteration */
	if(FLAME_outputs == NULL)
	{
		current_FLAME_output = add_FLAME_output(&FLAME_outputs);
		current_FLAME_output->type   = 0; /* snapshot */
		current_FLAME_output->format = 0; /* xml */
		current_FLAME_output->location = (char *)malloc( (strlen(filelocation) +  1) * sizeof(char));
		strcpy(current_FLAME_output->location, filelocation); /* location = 0.xml location */
		current_FLAME_output->period = 1; /* every iteration */
		current_FLAME_output->phase  = 0; /* no phase */
	}
	
	/* Print output settings to CLI */
	for(current_FLAME_output = FLAME_outputs; current_FLAME_output != NULL; current_FLAME_output = current_FLAME_output->next)
	{
		printf("output: type='");
		if(current_FLAME_output->type == 0) printf("snapshot");
		else if(current_FLAME_output->type == 1) printf("agent' name='Agent");
		else printf("undefined");
		printf("' format='");
		if(current_FLAME_output->format == 0) printf("xml");
		else printf("undefined");
		printf("' location='%s'", current_FLAME_output->location);
		printf(" period='%d' phase='%d'\n", current_FLAME_output->period, current_FLAME_output->phase);
	}

	/* Make sure cloud data makes sense if any of x,y,z coords were all the same */
	if ( partition_method == geometric ) {
		if ( cloud_data[0] == cloud_data[1] ) {
			cloud_data[0] = -SPINF;
			cloud_data[1] = SPINF;
		}
		if ( cloud_data[2] == cloud_data[3] ) {
			cloud_data[2] = -SPINF;
			cloud_data[3] = SPINF;
		}
		if ( cloud_data[4] == cloud_data[5] ) {
			cloud_data[4] = -SPINF;
			cloud_data[5] = SPINF;
		}
	}
}

/** \fn void write_int_static_array(FILE *file, $name * temp)
 * \brief Writes int.
 */
void write_int_static_array(FILE *file, int * temp, int size)
{
	int i;
	char data[1000];

	fputs("{", file);
	for(i=0; i<size; i++)
	{
		assert(!((temp[i])!=(temp[i])));
		assert(temp[i] < FLAME_INT_MAX);
		assert(temp[i] > FLAME_INT_MIN);
		sprintf(data, "%i", temp[i]);
		fputs(data, file);
		if(i < size-1) fputs(", ", file);
	}
	fputs("}", file);
}

/** \fn void write_float_static_array(FILE *file, float * temp)
 * \brief Writes float.
 */
void write_float_static_array(FILE *file, float * temp, int size)
{
	int i;
	char data[1000];

	fputs("{", file);
	for(i=0; i<size; i++)
	{
		assert(!((temp[i])!=(temp[i])));
		assert(temp[i] < FLAME_DOUBLE_MAX);
		assert(temp[i] > FLAME_DOUBLE_MIN);
		sprintf(data, "%f", temp[i]);
		fputs(data, file);
		if(i < size-1) fputs(", ", file);
	}
	fputs("}", file);
}

/** \fn void write_double_static_array(FILE *file, double * temp)
 * \brief Writes double.
 */
void write_double_static_array(FILE *file, double * temp, int size)
{
	int i;
	char data[1000];

	fputs("{", file);
	for(i=0; i<size; i++)
	{
		assert(!((temp[i])!=(temp[i])));
		assert(temp[i] < FLAME_DOUBLE_MAX);
		assert(temp[i] > FLAME_DOUBLE_MIN);
		sprintf(data, "%f", temp[i]);
		fputs(data, file);
		if(i < size-1) fputs(", ", file);
	}
	fputs("}", file);
}

/** \fn void write_char_static_array(FILE *file, char * temp)
 * \brief Writes char.
 */
void write_char_static_array(FILE *file, char * temp, int size)
{
	int i;
	char data[1000];

	//fputs("{", file);
	for(i=0; i<size; i++)
	{
		sprintf(data, "%c", temp[i]);
		fputs(data, file);
		//if(i < size-1) fputs(", ", file);
	}
	//fputs("}", file);
}

/** \fn void write_int_dynamic_array(FILE *file, int_array* temp)
 * \brief Writes int.
 */
void write_int_dynamic_array(FILE *file, int_array * temp)
{
	int i;
	char data[1000];

	fputs("{", file);
	for(i=0; i<(*temp).size; i++)
	{
		assert(!(((*temp).array[i])!=((*temp).array[i])));
		assert((*temp).array[i] < FLAME_INT_MAX);
		assert((*temp).array[i] > FLAME_INT_MIN);
		sprintf(data, "%i", (*temp).array[i]);
		fputs(data, file);
		if(i < ((*temp).size-1)) fputs(", ", file);
	}
	fputs("}", file);
}

/** \fn void write_float_dynamic_array(FILE *file, float_array* temp)
 * \brief Writes float.
 */
void write_float_dynamic_array(FILE *file, float_array * temp)
{
	int i;
	char data[1000];

	fputs("{", file);
	for(i=0; i<(*temp).size; i++)
	{
		assert(!(((*temp).array[i])!=((*temp).array[i])));
		assert((*temp).array[i] < FLAME_DOUBLE_MAX);
		assert((*temp).array[i] > FLAME_DOUBLE_MIN);
		sprintf(data, "%f", (*temp).array[i]);
		fputs(data, file);
		if(i < ((*temp).size-1)) fputs(", ", file);
	}
	fputs("}", file);
}

/** \fn void write_double_dynamic_array(FILE *file, double_array* temp)
 * \brief Writes double.
 */
void write_double_dynamic_array(FILE *file, double_array * temp)
{
	int i;
	char data[1000];

	fputs("{", file);
	for(i=0; i<(*temp).size; i++)
	{
		assert(!(((*temp).array[i])!=((*temp).array[i])));
		assert((*temp).array[i] < FLAME_DOUBLE_MAX);
		assert((*temp).array[i] > FLAME_DOUBLE_MIN);
		sprintf(data, "%f", (*temp).array[i]);
		fputs(data, file);
		if(i < ((*temp).size-1)) fputs(", ", file);
	}
	fputs("}", file);
}

/** \fn void write_char_dynamic_array(FILE *file, char_array* temp)
 * \brief Writes char.
 */
void write_char_dynamic_array(FILE *file, char_array * temp)
{
	int i;
	char data[1000];

	for(i=0; i<(*temp).size; i++)
	{
		sprintf(data, "%c", (*temp).array[i]);
		fputs(data, file);
	}
}



void write_Agent_agent(FILE *file, xmachine_memory_Agent * current)
{
	char data[1000];
	fputs("<xagent>\n" , file);
	fputs("<name>Agent</name>\n", file);
		fputs("<id>", file);
	
	assert(!((current->id)!=(current->id)));
	assert(current->id < FLAME_DOUBLE_MAX);
	assert(current->id > FLAME_DOUBLE_MIN);
	sprintf(data, "%i", current->id);
	fputs(data, file);
	fputs("</id>\n", file);
		fputs("<x>", file);
	
	assert(!((current->x)!=(current->x)));
	assert(current->x < FLAME_DOUBLE_MAX);
	assert(current->x > FLAME_DOUBLE_MIN);
	sprintf(data, "%f", current->x);
	fputs(data, file);
	fputs("</x>\n", file);
		fputs("<y>", file);
	
	assert(!((current->y)!=(current->y)));
	assert(current->y < FLAME_DOUBLE_MAX);
	assert(current->y > FLAME_DOUBLE_MIN);
	sprintf(data, "%f", current->y);
	fputs(data, file);
	fputs("</y>\n", file);
		fputs("<a>", file);
	
	assert(!((current->a)!=(current->a)));
	assert(current->a < FLAME_DOUBLE_MAX);
	assert(current->a > FLAME_DOUBLE_MIN);
	sprintf(data, "%f", current->a);
	fputs(data, file);
	fputs("</a>\n", file);
		fputs("<b>", file);
	
	assert(!((current->b)!=(current->b)));
	assert(current->b < FLAME_DOUBLE_MAX);
	assert(current->b > FLAME_DOUBLE_MIN);
	sprintf(data, "%f", current->b);
	fputs(data, file);
	fputs("</b>\n", file);

	fputs("</xagent>\n", file);
}


void FLAME_write_xml(char * location, int iteration_number, int * output_types, int output_type_size)
{
	/* Pointer to file */
	FILE *file;
	char data[1000];
	
		sprintf(data, "%s%i.xml", location, iteration_number);
	
	if((file = fopen(data, "w"))==NULL)
	{
		printf("Error: cannot open file '%s' for writing\n", data);
		exit(0);
	}
	
	
	fputs("<states>\n", file);
	if(FLAME_integer_in_array(0, output_types, output_type_size))
	{
		fputs("<itno>", file);
		sprintf(data, "%i", iteration_number);
		fputs(data, file);
		fputs("</itno>\n", file);
		fputs("<environment>\n" , file);
			fputs("<set_no>", file);
		sprintf(data, "%i", FLAME_environment_variable_set_no);
		fputs(data, file);
		fputs("</set_no>\n", file);
			fputs("<run>", file);
		sprintf(data, "%i", FLAME_environment_variable_run);
		fputs(data, file);
		fputs("</run>\n", file);
			fputs("<const_radius>", file);
		sprintf(data, "%f", FLAME_environment_variable_const_radius);
		fputs(data, file);
		fputs("</const_radius>\n", file);
			fputs("<const_b>", file);
		sprintf(data, "%f", FLAME_environment_variable_const_b);
		fputs(data, file);
		fputs("</const_b>\n", file);
			fputs("</environment>\n" , file);
	}
	
	
	if(FLAME_integer_in_array(0, output_types, output_type_size) || FLAME_integer_in_array(1, output_types, output_type_size))
	{
		current_xmachine_Agent_holder = Agent_start_Agent_state->agents;
			while(current_xmachine_Agent_holder)
			{
				write_Agent_agent(file, current_xmachine_Agent_holder->agent);

				current_xmachine_Agent_holder = current_xmachine_Agent_holder->next;
			}
	}
	
	fputs("</states>\n" , file);

	/* Close the file */
	(void)fclose(file);
}

/** \fn void saveiterationdata(int iteration_number)
 * \brief Save X-machine memory to a file.
 * \param iteration_number The current iteration number.
 */
void saveiterationdata(int iteration_number)
{
	FLAME_output * current_FLAME_output;
	FLAME_output * current_FLAME_output2;
	int output_types[1000];
	int output_type_size = 0;

	/* For each output */
	for(current_FLAME_output = FLAME_outputs; current_FLAME_output != NULL; current_FLAME_output = current_FLAME_output->next)
	{
		/* If period/phase equates to current iteration */
		if(iteration_number%current_FLAME_output->period == current_FLAME_output->phase)
		{
			/* If output has already been handled */
			if(current_FLAME_output->flag == 0)
			{
				/* Check snapshot */
				if(current_FLAME_output->type == 0)
				{
					//snapshot_location = current_FLAME_output->location;
					output_types[0] = 0;
					FLAME_write_xml(current_FLAME_output->location, iteration_number, output_types, 1);
					/* Set flag to 1 and every output to same location */
					current_FLAME_output->flag = 1;
					for(current_FLAME_output2 = FLAME_outputs; current_FLAME_output2 != NULL; current_FLAME_output2 = current_FLAME_output2->next)
					{
						if(strcmp(current_FLAME_output->location, current_FLAME_output2->location) == 0)
						{
							current_FLAME_output2->flag = 1;
						}
					}
				}
				if(current_FLAME_output->type == 1)
				{
					/* Reinitialise agent size */
					output_type_size = 0;
					output_types[0] = 1;
					
					current_FLAME_output->flag = 1;
					for(current_FLAME_output2 = FLAME_outputs; current_FLAME_output2 != NULL; current_FLAME_output2 = current_FLAME_output2->next)
					{
						if(current_FLAME_output2->flag == 0 && strcmp(current_FLAME_output->location, current_FLAME_output2->location) == 0)
						{
							output_types[++output_type_size] = current_FLAME_output2->type;
							
							current_FLAME_output2->flag = 1;
						}
					}
					
					FLAME_write_xml(current_FLAME_output->location, iteration_number, output_types, output_type_size);
				}
			}
		}
	}
	/* Set flags back to 0 */
	for(current_FLAME_output = FLAME_outputs; current_FLAME_output != NULL; current_FLAME_output = current_FLAME_output->next)
	{
		current_FLAME_output->flag = 0;
	}
}
