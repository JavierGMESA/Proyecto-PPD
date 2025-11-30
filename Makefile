# --- Configuración general ---
CC          = gcc
CC_MPI      = mpicc
CFLAGS      = -Wall -O2
CFLAGS_PARAL= -Wall -O2 -fopenmp
CFLAGS_DISTR= -Wall -O2 -std=c11
CFLAGS_HIBR = -Wall -O2 -std=c11 -fopenmp

TARGETS = cga_onemax cga_izhi_onemax \
          cga_paral_onemax cga_paral_izhi_onemax \
          cga_distrib_onemax cga_distrib_izhi_onemax \
          cga_hibrid_onemax cga_hibrid_izhi_onemax

# --- Objetos comunes ---
OBJS_ONEMAX    = onemax.o
OBJS_ONEMAX_MPI= onemax.o onemax_mpi.o

# --- Regla por defecto ---
all: $(TARGETS)

# --- Objetos comunes ---
onemax.o: onemax.c onemax.h cga_param.h
	$(CC) $(CFLAGS) -c onemax.c

onemax_mpi.o: onemax_mpi.c onemax_mpi.h onemax.h cga_param.h
	$(CC_MPI) $(CFLAGS_DISTR) -c onemax_mpi.c

# --- Secuenciales ---
cga_onemax: cga_onemax.c cga_param.h onemax.o
	$(CC) $(CFLAGS) -o $@ cga_onemax.c $(OBJS_ONEMAX)

cga_izhi_onemax: cga_izhi_onemax.c cga_param.h onemax.o
	$(CC) $(CFLAGS) -o $@ cga_izhi_onemax.c $(OBJS_ONEMAX)

# --- OpenMP ---
cga_paral_onemax: cga_paral_onemax.c cga_param.h onemax.o
	$(CC) $(CFLAGS_PARAL) -o $@ cga_paral_onemax.c $(OBJS_ONEMAX)

cga_paral_izhi_onemax: cga_paral_izhi_onemax.c cga_param.h onemax.o
	$(CC) $(CFLAGS_PARAL) -o $@ cga_paral_izhi_onemax.c $(OBJS_ONEMAX)

# --- MPI (distribuidos) ---
cga_distrib_onemax: cga_distrib_onemax.c cga_param.h onemax.o onemax_mpi.o
	$(CC_MPI) $(CFLAGS_DISTR) -o $@ cga_distrib_onemax.c $(OBJS_ONEMAX_MPI)

cga_distrib_izhi_onemax: cga_distrib_izhi_onemax.c cga_param.h onemax.o onemax_mpi.o
	$(CC_MPI) $(CFLAGS_DISTR) -o $@ cga_distrib_izhi_onemax.c $(OBJS_ONEMAX_MPI)

# --- Híbridos (MPI + OpenMP) ---
cga_hibrid_onemax: cga_hibrid_onemax.c cga_param.h onemax.o onemax_mpi.o
	$(CC_MPI) $(CFLAGS_HIBR) -o $@ cga_hibrid_onemax.c $(OBJS_ONEMAX_MPI)

cga_hibrid_izhi_onemax: cga_hibrid_izhi_onemax.c cga_param.h onemax.o onemax_mpi.o
	$(CC_MPI) $(CFLAGS_HIBR) -o $@ cga_hibrid_izhi_onemax.c $(OBJS_ONEMAX_MPI)

# --- Limpiar binarios y temporales ---
clean:
	rm -f $(TARGETS) *.o


