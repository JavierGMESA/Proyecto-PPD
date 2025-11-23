# --- Configuración general ---
CC = gcc
CFLAGS = -Wall -O2
CFLAGS_PARAL = -Wall -O2 -fopenmp
TARGETS = cga_onemax cga_izhi_onemax cga_paral_onemax cga_paral2_izhi_onemax

# --- Archivos de cabecera ---
HEADERS = cga_param.h

# --- Regla por defecto ---
all: $(TARGETS)

# --- Compilar cga_onemax ---
cga_onemax: cga_onemax.c cga_param.h
	$(CC) $(CFLAGS) -o $@ cga_onemax.c

# --- Compilar cga_izhi_onemax ---
cga_izhi_onemax: cga_izhi_onemax.c cga_param.h
	$(CC) $(CFLAGS) -o $@ cga_izhi_onemax.c

cga_paral_onemax: cga_paral_onemax.c cga_param.h
	$(CC) $(CFLAGS_PARAL) -o $@ cga_onemax.c

cga_paral2_izhi_onemax: cga_paral2_izhi_onemax.c cga_param.h
	$(CC) $(CFLAGS_PARAL) -o $@ cga_paral_izhi_onemax.c

# --- Limpiar binarios y temporales ---
clean:
	rm -f $(TARGETS) *.o

