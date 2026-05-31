#include "header.h"
#include "parquet_engine.h"


void write_parquet_data_Agent(int iteration_no) {
    parquet_clear_buffer("Agent");

    // Fix: Explicitly cast the generic xmachine* pointer to the specific agent holder type
    struct xmachine_memory_Agent_holder *current_holder = (struct xmachine_memory_Agent_holder *)(*current_node).agents;
    
    while(current_holder != NULL) {
        
        // Extract the actual agent structure from the active holder node
        current_xmachine_Agent = current_holder->agent;
        
        long agent_id = (long)current_xmachine_Agent->id;

        // Register the row context once for this specific agent instance
        parquet_start_row("Agent", iteration_no, agent_id);

        // Dynamically unroll and pass every single model variable definition
        
        parquet_buffer_variable(
            "Agent", 
            "id", 
            (double)current_xmachine_Agent->id
        );
        
        parquet_buffer_variable(
            "Agent", 
            "x", 
            (double)current_xmachine_Agent->x
        );
        
        parquet_buffer_variable(
            "Agent", 
            "y", 
            (double)current_xmachine_Agent->y
        );
        
        parquet_buffer_variable(
            "Agent", 
            "a", 
            (double)current_xmachine_Agent->a
        );
        
        parquet_buffer_variable(
            "Agent", 
            "b", 
            (double)current_xmachine_Agent->b
        );
        
        
        // Advance to the next holder element in the linked list
        current_holder = current_holder->next;
    }

    parquet_write_file("Agent", iteration_no);
}


#ifdef __cplusplus
extern "C" {
#endif

void saveiterationdata_parquet(int iteration_no) {
    // Dynamically trigger the write function for every agent defined in the model
    
    write_parquet_data_Agent(iteration_no);
    
}

#ifdef __cplusplus
}
#endif
