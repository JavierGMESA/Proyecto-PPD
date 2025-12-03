#ifndef ONEMAX_MPI
#define ONEMAX_MPI

#include <stdlib.h>
#include <time.h>
#include <stdio.h>
#include <mpi.h>
#include "cga_param.h"
#include "truck.hpp"

// Comunicación de individuos MPI
Individuo* MPI_Comunicacion(const Individuo* mejor, const unsigned num_ejecuciones);

#endif