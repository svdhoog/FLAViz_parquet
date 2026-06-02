# ==========================================================================
# FLAME AUTOMATED GENERATION MAKEFILE TEMPLATE WITH PARQUET SERIALIZATION
# ==========================================================================

# Message Board Library paths
LIBMBOARD_DIR = /home/sander/build/libmboard
LIBMBOARD_INC = $(LIBMBOARD_DIR)/include
LIBMBOARD_LIB = $(LIBMBOARD_DIR)/lib

# Compilers and Loaders (Using g++ for linking mixed C/C++ objects)
SERIAL_CCOMP    = gcc
PARALLEL_CCOMP  = mpicc
SERIAL_LOADER   = g++
PARALLEL_LOADER = mpicxx

# Feature Flags
DEFINES         =


# Toolchain Assignment
CC       = $(SERIAL_CCOMP)
CXX      = g++
LD       = $(SERIAL_LOADER)

# Compilation Flags (Included -I. so generated source files can find parquet_engine.h)
CFLAGS   = -I$(LIBMBOARD_INC) -I. $(DEFINES) -fcommon -Wall
CXXFLAGS = -I$(LIBMBOARD_INC) -I. $(DEFINES) -Wall -std=c++20


CFLAGS   += -std=c11 -D_DEBUG_MODE -g
CXXFLAGS += -D_DEBUG_MODE -g




LDFLAGS  = -L$(LIBMBOARD_LIB)

# Library Dependencies (Standard FLAME + Apache Arrow ecosystem)
LIBS     = -lmboard_sd  -lm
LIBS    += -larrow -lparquet -lstdc++


# FLAME Core Source manifests
FLAME    = main.c memory.c xml.c messageboards.c partitioning.c rules.c timing.c
AUX      = stategraph.dot stategraph_colour.dot process_order_graph.dot Doxyfile latex.tex

# Dynamic Model Manifests (Parsed dynamically by xparser)
SOURCES  =  agent_functions.c 
HEADERS  = header.h low_primes.h mboard.h parquet_engine.h  Agent_agent_header.h 

# External Parquet Tracking System Engine Code
PARQUET_SRC = parquet.cpp parquet_engine.cpp

# Consolidated dependencies (Dynamic generation drops parquet_engine.h straight into place)
DEPS     = Makefile header.h low_primes.h parquet_engine.h

# Unified Object target arrays derived dynamically from source collections
OBJECTS  = $(SOURCES:.c=.o) $(FLAME:.c=.o) $(PARQUET_SRC:.cpp=.o)
EXECUTABLE = main
RM       = rm -f

# Pipeline Execution Targets
all: $(SOURCES) $(FLAME) $(EXECUTABLE)

$(EXECUTABLE): $(OBJECTS)
	$(LD) $(LDFLAGS) $(OBJECTS) -o $@ $(LIBS)

# Core objects depend on native framework headers and generated parquet engine header
$(OBJECTS): $(DEPS)

# Structural Suffix Processing Patterns
.c.o:
	$(CC) -c $(CFLAGS) $< -o $@

.cpp.o:
	$(CXX) -c $(CXXFLAGS) $< -o $@

# Cleanup Framework Operations (Preserving your *.parquet data files)
clean:
	$(RM) $(OBJECTS) $(EXECUTABLE) $(EXECUTABLE).exe

vclean:
	$(RM) main $(EXECUTABLE) $(EXECUTABLE).exe $(OBJECTS) $(FLAME) $(HEADERS) $(AUX) Makefile

format:
	astyle -A3 $(SOURCES)
	for file in $(patsubst %.c,%.h, $(SOURCES)) ; \
	do \
		echo $$file ; \
		astyle -A3 $$file ; \
	done 

print:
	a2ps -R -f10 --column=1 $(SOURCES)
	