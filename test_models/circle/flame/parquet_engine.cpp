#include "parquet_engine.h"
#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <map>

struct AgentBuffer {
    std::vector<int> iterations;
    std::vector<long> ids;
    std::map<std::string, std::vector<double>> columns;
};

static std::unordered_map<std::string, AgentBuffer> global_buffers;

extern "C" {

void parquet_clear_buffer(const char* agent_name) {
    std::string agent(agent_name);
    auto& buf = global_buffers[agent];
    
    buf.iterations.clear();
    buf.ids.clear();
    
    
    if (agent == "Agent") {
        
        buf.columns["id"].clear();
        
        buf.columns["x"].clear();
        
        buf.columns["y"].clear();
        
        buf.columns["a"].clear();
        
        buf.columns["b"].clear();
        
    }
    
}

void parquet_start_row(const char* agent_name, int iteration, long id) {
    auto& buf = global_buffers[std::string(agent_name)];
    buf.iterations.push_back(iteration);
    buf.ids.push_back(id);
}

void parquet_buffer_variable(const char* agent_name, const char* var_name, double value) {
    auto& buf = global_buffers[std::string(agent_name)];
    buf.columns[std::string(var_name)].push_back(value);
}

void parquet_write_file(const char* agent_name, int iteration) {
    std::string agent(agent_name);
    auto& buf = global_buffers[agent];

    if (buf.iterations.empty()) return;

    // Direct sanity verification trace check before calling Apache Arrow
    std::cout << "[Parquet Engine] Verifying structural layout for " << agent << ":\n"
              << "  -> Primary Metadata Records (Rows): " << buf.iterations.size() << "\n";
              
    for (const auto& [col_name, col_vec] : buf.columns) {
        std::cout << "  -> Column '" << col_name << "' size: " << col_vec.size() << "\n";
        if (col_vec.size() != buf.iterations.size()) {
            std::cerr << "  [CRITICAL ERROR] Size mismatch detected in column " << col_name 
                      << "! Parquet generation aborted to prevent corruption.\n";
            return;
        }
    }

    // --- Apache Arrow Serializer Pipeline ---
    // At this point, your Arrow / Parquet array builders can consume the 
    // identically sized vectors safely without throwing memory allocation faults.
    std::cout << "  -> Structure Verified. Writing file out to disk..." << std::endl;
}

} // extern "C"
