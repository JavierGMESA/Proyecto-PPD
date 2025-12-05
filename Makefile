# --- Configuración general ---
CC          = gcc
CXX         = g++
CC_MPI      = mpicc
CXX_MPI     = mpic++
CFLAGS      = -Wall -O2
CFLAGS_PARAL= -Wall -O2 -fopenmp
CFLAGS_DISTR= -Wall -O2 -std=c11
CFLAGS_HIBR = -Wall -O2 -std=c11 -fopenmp
CXXFLAGS    = -Wall -O2 -std=c++17

TARGETS = cga_onemax cga_izhi_onemax \
          cga_paral_onemax cga_paral_izhi_onemax \
          cga_distrib_onemax cga_distrib_izhi_onemax \
          cga_hibrid_onemax cga_hibrid_izhi_onemax \
          cga_truck cga_izhi_truck \
          cga_paral_truck cga_paral_izhi_truck \
          cga_distrib_truck cga_distrib_izhi_truck \
          cga_hibrid_truck cga_hibrid_izhi_truck

# --- Objetos comunes ONEMAX (C) ---
OBJS_ONEMAX     = onemax.o
OBJS_ONEMAX_MPI = onemax.o onemax_mpi.o

# --- Objetos comunes TRUCK (C++) ---
TRUCK_OBJS      = truck.o HybridTruckEvaluator.o
TRUCK_MPI_OBJS  = truck.o truck_mpi.o HybridTruckEvaluator.o

# --- Regla por defecto ---
all: $(TARGETS)

# =========================
# OBJETOS C (ONEMAX)
# =========================
onemax.o: onemax.c onemax.h cga_param.h
	$(CC) $(CFLAGS) -c onemax.c

onemax_mpi.o: onemax_mpi.c onemax_mpi.h onemax.h cga_param.h
	$(CC_MPI) $(CFLAGS_DISTR) -c onemax_mpi.c

# =========================
# OBJETOS C++ (TRUCK)
# =========================
truck.o: truck.cpp truck.hpp cga_param.h HybridTruckEvaluator.h
	$(CXX) $(CXXFLAGS) -c truck.cpp

truck_mpi.o: truck_mpi.cpp truck_mpi.hpp truck.hpp cga_param.h HybridTruckEvaluator.h
	$(CXX_MPI) $(CXXFLAGS) -c truck_mpi.cpp

HybridTruckEvaluator.o: HybridTruckEvaluator.cpp HybridTruckEvaluator.h
	$(CXX) $(CXXFLAGS) -c HybridTruckEvaluator.cpp

# =========================
# SECUENCIALES (ONEMAX)
# =========================
cga_onemax: cga_onemax.c cga_param.h onemax.o
	$(CC) $(CFLAGS) -o $@ cga_onemax.c $(OBJS_ONEMAX)

cga_izhi_onemax: cga_izhi_onemax.c cga_param.h onemax.o
	$(CC) $(CFLAGS) -o $@ cga_izhi_onemax.c $(OBJS_ONEMAX)

# =========================
# OPENMP (ONEMAX)
# =========================
cga_paral_onemax: cga_paral_onemax.c cga_param.h onemax.o
	$(CC) $(CFLAGS_PARAL) -o $@ cga_paral_onemax.c $(OBJS_ONEMAX)

cga_paral_izhi_onemax: cga_paral_izhi_onemax.c cga_param.h onemax.o
	$(CC) $(CFLAGS_PARAL) -o $@ cga_paral_izhi_onemax.c $(OBJS_ONEMAX)

# =========================
# MPI (ONEMAX)
# =========================
cga_distrib_onemax: cga_distrib_onemax.c cga_param.h onemax.o onemax_mpi.o
	$(CC_MPI) $(CFLAGS_DISTR) -o $@ cga_distrib_onemax.c $(OBJS_ONEMAX_MPI)

cga_distrib_izhi_onemax: cga_distrib_izhi_onemax.c cga_param.h onemax.o onemax_mpi.o
	$(CC_MPI) $(CFLAGS_DISTR) -o $@ cga_distrib_izhi_onemax.c $(OBJS_ONEMAX_MPI)

# =========================
# HÍBRIDOS (ONEMAX)
# =========================
cga_hibrid_onemax: cga_hibrid_onemax.c cga_param.h onemax.o onemax_mpi.o
	$(CC_MPI) $(CFLAGS_HIBR) -o $@ cga_hibrid_onemax.c $(OBJS_ONEMAX_MPI)

cga_hibrid_izhi_onemax: cga_hibrid_izhi_onemax.c cga_param.h onemax.o onemax_mpi.o
	$(CC_MPI) $(CFLAGS_HIBR) -o $@ cga_hibrid_izhi_onemax.c $(OBJS_ONEMAX_MPI)

# =========================
# SECUENCIALES (TRUCK, C++)
# =========================
cga_truck: cga_truck.cpp cga_param.h truck.hpp $(TRUCK_OBJS)
	$(CXX) $(CXXFLAGS) -o $@ cga_truck.cpp $(TRUCK_OBJS)

cga_izhi_truck: cga_izhi_truck.cpp cga_param.h truck.hpp $(TRUCK_OBJS)
	$(CXX) $(CXXFLAGS) -o $@ cga_izhi_truck.cpp $(TRUCK_OBJS)

# =========================
# OPENMP (TRUCK, C++)
# =========================
cga_paral_truck: cga_paral_truck.cpp cga_param.h truck.hpp $(TRUCK_OBJS)
	$(CXX) $(CXXFLAGS) -fopenmp -o $@ cga_paral_truck.cpp $(TRUCK_OBJS)

cga_paral_izhi_truck: cga_paral_izhi_truck.cpp cga_param.h truck.hpp $(TRUCK_OBJS)
	$(CXX) $(CXXFLAGS) -fopenmp -o $@ cga_paral_izhi_truck.cpp $(TRUCK_OBJS)

# =========================
# MPI (TRUCK, C++)
# =========================
cga_distrib_truck: cga_distrib_truck.cpp cga_param.h truck.hpp $(TRUCK_MPI_OBJS)
	$(CXX_MPI) $(CXXFLAGS) -o $@ cga_distrib_truck.cpp $(TRUCK_MPI_OBJS)

cga_distrib_izhi_truck: cga_distrib_izhi_truck.cpp cga_param.h truck.hpp $(TRUCK_MPI_OBJS)
	$(CXX_MPI) $(CXXFLAGS) -o $@ cga_distrib_izhi_truck.cpp $(TRUCK_MPI_OBJS)

# =========================
# HÍBRIDOS (TRUCK, C++)
# =========================
cga_hibrid_truck: cga_hibrid_truck.cpp cga_param.h truck.hpp $(TRUCK_MPI_OBJS)
	$(CXX_MPI) $(CXXFLAGS) -fopenmp -o $@ cga_hibrid_truck.cpp $(TRUCK_MPI_OBJS)

cga_hibrid_izhi_truck: cga_hibrid_izhi_truck.cpp cga_param.h truck.hpp $(TRUCK_MPI_OBJS)
	$(CXX_MPI) $(CXXFLAGS) -fopenmp -o $@ cga_hibrid_izhi_truck.cpp $(TRUCK_MPI_OBJS)

# --- Limpiar binarios y temporales ---
clean:
	rm -f $(TARGETS) *.o



