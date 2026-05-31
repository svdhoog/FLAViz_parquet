#ifndef PARQUET_ENGINE_H
#define PARQUET_ENGINE_H

#ifdef __cplusplus
extern "C" {
#endif

// Allocates a new row record with identity metadata before streaming its variables
void parquet_start_row(const char* agent_name, int iteration, long id);

// Streams an individual column value for the current active row record
void parquet_buffer_variable(const char* agent_name, const char* var_name, double value);

// Lifecycle hooks
void parquet_clear_buffer(const char* agent_name);
void parquet_write_file(const char* agent_name, int iteration);

// Save iteration data to parquet
void saveiterationdata_parquet(int iteration_no);

#ifdef __cplusplus
}
#endif

#endif // PARQUET_ENGINE_H
