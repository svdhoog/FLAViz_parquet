#include "header.h"
#include "parquet_engine.h"
#include <stdio.h>
#include <string>
    

void write_parquet_data_Agent(int iteration_no) {
    // Clear out any stale records in the C++ backend buffer for this agent type
    parquet_clear_buffer("Agent");

    int active_records_buffered = 0;

    // FIX: Leverage your framework's native structural loop macros
    // This expands perfectly to walk the active agent list state
    START_LOOP_OVER_Agent_AGENTS
        
        // The macro automatically unpacks and assigns 'current_xmachine_Agent' for us!
        long agent_id = (long)current_xmachine_Agent->id;

        // Register the row context once for this specific agent instance
        parquet_start_row("Agent", iteration_no, agent_id);

        // Dynamically unroll and pass every single model variable definition
        
        parquet_buffer_variable(
            "Agent",  // Name of the agent class
            "id",        // Name of this specific variable
            (double)current_xmachine_Agent->id
        );
        
        parquet_buffer_variable(
            "Agent",  // Name of the agent class
            "x",        // Name of this specific variable
            (double)current_xmachine_Agent->x
        );
        
        parquet_buffer_variable(
            "Agent",  // Name of the agent class
            "y",        // Name of this specific variable
            (double)current_xmachine_Agent->y
        );
        
        parquet_buffer_variable(
            "Agent",  // Name of the agent class
            "a",        // Name of this specific variable
            (double)current_xmachine_Agent->a
        );
        
        parquet_buffer_variable(
            "Agent",  // Name of the agent class
            "b",        // Name of this specific variable
            (double)current_xmachine_Agent->b
        );
        
        
        active_records_buffered++;

    END_LOOP_OVER_Agent_AGENTS

    fprintf(stdout, "  [PARQUET TRAVERSAL] Agent: %s | Records buffered: %d\n", 
            "Agent", active_records_buffered);
    fflush(stdout);

    // Only commit the file to disk if records were actually found and buffered
    if (active_records_buffered > 0) {
        parquet_write_file("Agent", iteration_no);
    } else {
        fprintf(stdout, "  [PARQUET SKIP] Skipping file write for %s: Buffer is empty.\n", "Agent");
        fflush(stdout);
    }
}


#ifdef __cplusplus
extern "C" {
#endif

// Define the storage allocation for our global directory string
char parquet_output_directory[512] = {0};

void saveiterationdata_parquet(int iteration_no) {
    
    // On the first iteration, resolve the directory prefix from outputpath
    if (iteration_no == 1 && parquet_output_directory[0] == '\0') {
        // Bind directly to the native FLAME output path character array
        extern char outputpath[]; 
        
        // FIX: Removed 'outputpath != NULL' to satisfy the strict compiler array-address check
        if (outputpath[0] != '\0') {
            std::string full_path(outputpath);
            size_t last_slash = full_path.find_last_of("/\\");
            
            if (last_slash != std::string::npos) {
                // Extract everything up to and including the trailing slash
                std::string dir = full_path.substr(0, last_slash + 1);
                snprintf(parquet_output_directory, sizeof(parquet_output_directory), "%s", dir.c_str());
            } else {
                // No slashes found means the file is in the Current Working Directory
                parquet_output_directory[0] = '\0';
            }
        }
    }

    fprintf(stdout, "\n>>> [PARQUET CORE] Entering saveiterationdata_parquet() for iteration %d...\n", iteration_no);
    fflush(stdout);

    
    write_parquet_data_Agent(iteration_no);
    
    
    fprintf(stdout, ">>> [PARQUET CORE] Completed processing cycle for iteration %d.\n\n", iteration_no);
    fflush(stdout);
}

#ifdef __cplusplus
}
#endif
