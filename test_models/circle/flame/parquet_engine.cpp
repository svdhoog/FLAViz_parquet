#include "parquet_engine.h"
#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <map>

// Include mandatory Apache Arrow and Parquet C++ headers
#include <arrow/api.h>
#include <arrow/io/api.h>
#include <parquet/arrow/writer.h>

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
    std::cout << "  -> Structure Verified. Writing file out to disk..." << std::endl;

    arrow::Status status;
    arrow::MemoryPool* pool = arrow::default_memory_pool();
    
    // 1. Create native Arrow array builders for structural tracking metadata
    arrow::Int32Builder iter_builder(pool);
    arrow::Int64Builder id_builder(pool);
    
    // Populate the base column builders with data from our structural std::vectors
    status = iter_builder.AppendValues(buf.iterations);
    if (!status.ok()) { std::cerr << "  [ARROW ERROR] Appending iterations failed: " << status.ToString() << "\n"; return; }
    
    status = id_builder.AppendValues(buf.ids);
    if (!status.ok()) { std::cerr << "  [ARROW ERROR] Appending agent IDs failed: " << status.ToString() << "\n"; return; }

    // Prepare arrays to hold our structural Schema fields and corresponding Table Column arrays
    arrow::FieldVector schema_fields;
    arrow::ArrayVector table_arrays;

    // Push the metadata mapping properties into our table configuration fields
    schema_fields.push_back(arrow::field("iteration", arrow::int32()));
    schema_fields.push_back(arrow::field("agent_id", arrow::int64()));
    
    std::shared_ptr<arrow::Array> arr_iter;
    std::shared_ptr<arrow::Array> arr_id;
    
    // FIXED: Capture and verify status to resolve [[nodiscard]] warning error
    status = iter_builder.Finish(&arr_iter);
    if (!status.ok()) { std::cerr << "  [ARROW ERROR] Completing iteration array failed: " << status.ToString() << "\n"; return; }

    status = id_builder.Finish(&arr_id);
    if (!status.ok()) { std::cerr << "  [ARROW ERROR] Completing agent ID array failed: " << status.ToString() << "\n"; return; }
    
    table_arrays.push_back(arr_iter);
    table_arrays.push_back(arr_id);

    // 2. Loop through our columns map and dynamically build floating-point array records
    for (const auto& [col_name, col_vec] : buf.columns) {
        arrow::DoubleBuilder col_builder(pool);
        status = col_builder.AppendValues(col_vec);
        if (!status.ok()) {
            std::cerr << "  [ARROW ERROR] Appending column " << col_name << " failed: " << status.ToString() << "\n";
            return;
        }
        
        std::shared_ptr<arrow::Array> arr_col;
        
        // FIXED: Capture and verify status inside the map iterator loop
        status = col_builder.Finish(&arr_col);
        if (!status.ok()) { std::cerr << "  [ARROW ERROR] Completing column array for " << col_name << " failed: " << status.ToString() << "\n"; return; }
        
        schema_fields.push_back(arrow::field(col_name, arrow::float64()));
        table_arrays.push_back(arr_col);
    }

    // 3. Complete the schema description definition layout and pack columns into an Arrow Table
    auto schema = std::make_shared<arrow::Schema>(schema_fields);
    auto table = arrow::Table::Make(schema, table_arrays);

    // 4. Construct the output file target path string inside the Current Working Directory
    // NOTE: Construct the output file target path relative to 0.xml location
    std::string filename = std::string(parquet_output_directory) + agent + "_" + std::to_string(iteration) + ".parquet";

    // 5. Instantiate a native operating system writable file descriptor stream context
    std::shared_ptr<arrow::io::FileOutputStream> outfile;
    auto create_res = arrow::io::FileOutputStream::Open(filename);
    if (!create_res.ok()) {
        std::cerr << "  [FILE IO ERROR] Could not open file context '" << filename 
                  << "' for writing. Status: " << create_res.status().ToString() << "\n";
        return;
    }
    outfile = create_res.ValueOrDie();

    // 6. Serialize the Table memory layout and compress it straight onto the physical disk
    status = parquet::arrow::WriteTable(*table, pool, outfile, 65536); // Standard 64KB row chunks
    if (!status.ok()) {
        std::cerr << "  [PARQUET WRITE FAILURE] Serialization pipeline crash: " << status.ToString() << "\n";
        return;
    }

    std::cout << "  [PARQUET SUCCESS] File safely committed: " << filename << std::endl;
}

} // extern "C"
