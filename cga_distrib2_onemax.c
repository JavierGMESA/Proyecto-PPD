/* --- Idea Principal del algoritmo ---
En lugar de trabajar todos juntos en un puzle gigante (como en el código anterior), cada proceso tiene su propia población completa (N_ROWS filas).
Como cada proceso usa una semilla aleatoria distinta (srand + rank), cada "isla" deberia explorar una zona diferente del espacio de búsqueda.
Para evitar que una isla se estanque, de vez en cuando (cada X generaciones) intercambian sus mejores individuos.

Cómo funciona ahora (Intercambio de Comunicación)
En este modelo, las islas son independientes el 90% del tiempo.
Trabajo Local: Cada procesador ejecuta el bucle genético en su propia memoria. No hay comunicación en cada generación. 
Esto lo hace rapidísimo.Frecuencia (MIG_INTERVAL): Solo cada 20(lo podemos cambiar) generaciones (o lo que definas), se activa el if.Intercambio (MPI_Sendrecv):
Se usa una topología de anillo.Si tienes 4 procesos: 0 --> 1 --> 2 --> 3 --> 0.
El Proceso 0 envía su MEJOR individuo al Proceso 1. El Proceso 0 recibe el MEJOR individuo del Proceso 
Cuando llega un individuo de fuera ("inmigrante"), buscamos al PEOR de nuestra población local y lo machacamos con el inmigrante (siempre que el inmigrante sea mejor).
Esto permite que si una isla se queda atascada en un óptimo local, 
la llegada de un individuo "fresco" de otra isla (que ha evolucionado con otra semilla aleatoria) le ayude a salir del bache.
*/

#include <mpi.h>    /*  */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "cga_param.h"

// Frecuencia de migración (cada cuántas generaciones intercambian datos)
#define MIG_INTERVAL 20 

typedef struct {
    int genes[L];
    int fitness;
} Individuo;

// ----------- FUNCIONES AUXILIARES (Originales) -----------
int rand_int(int min, int max) {
    return min + rand() % (max - min + 1);
}

float rand_float() {
    return (float) rand() / RAND_MAX;
}

// Evaluar OneMax
int evaluar(const Individuo *ind) {
    int s = 0;
    for (int i = 0; i < L; i++)
        s += ind->genes[i];
    return s;
}

// Inicializar individuo aleatorio
void inicializar_individuo(Individuo *ind) {
    for (int i = 0; i < L; i++)
        ind->genes[i] = rand_int(0, 1);
    ind->fitness = evaluar(ind);
}

// Copiar individuo
void copiar(Individuo *dest, const Individuo *src) {
    *dest = *src; // Copia directa de estructura
}

// Crossover de 1 punto
void crossover_1p(const Individuo *p1, const Individuo *p2, Individuo *hijo) {
    int punto = rand_int(1, L - 1);
    for (int i = 0; i < L; i++) {
        hijo->genes[i] = (i < punto) ? p1->genes[i] : p2->genes[i];
    }
}

// Mutación (10% de probabilidad de invertir un bit al azar)
void mutar(Individuo *ind) {
    if (rand_float() < MUT_PROB) {
        int pos = rand_int(0, L - 1);
        ind->genes[pos] = 1 - ind->genes[pos];
    }
}

// Obtener índice de vecino (Versión original intacta)
// Al ser modelo de islas, cada proceso tiene su matriz completa y bordes toroidales
void vecino_aleatorios(int fila, int col, int *fc) {
    int df[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};

    for (int k = 0; k < 2; k++) {
        int nf, nc;
        do {
            int dir = rand() % 4;
            nf = fila + df[dir];
            nc = col + dc[dir];
        } while (nf < 0 || nf >= N_ROWS || nc < 0 || nc >= N_COLS);

        fc[k * 2]     = nf;
        fc[k * 2 + 1] = nc;
    }
}

// ------------------ PROGRAMA PRINCIPAL ------------------

int main(int argc, char *argv[]) {

    // --- CAMBIO MPI: Inicialización ---
    int myrank, size;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    // --- CAMBIO MPI: Semilla distinta por isla ---
    // Esto es CRUCIAL: si no, todas las islas hacen exactamente lo mismo
    srand(time(NULL) + myrank * 1000);

    Individuo **poblacion, **nueva_poblacion;
    int i, j;
    
    Individuo hijo, mejor_individuo_local;
    int mejor_fitness_local = 0;
    int mejor_fitness_global_sistema = 0; // El mejor de TODAS las islas

    // Reserva de memoria (Completa, cada isla tiene su mundo)
    poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    nueva_poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    
    if(!poblacion || !nueva_poblacion) {
        printf("Error memoria\n");
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    
    for(i = 0; i < N_ROWS; ++i) {
        poblacion[i] = (Individuo*) calloc (N_COLS, sizeof(Individuo));
        nueva_poblacion[i] = (Individuo*) calloc (N_COLS, sizeof(Individuo));
    }

    // Inicializar población LOCAL de la isla
    for (i = 0; i < N_ROWS; i++) {
        for (j = 0; j < N_COLS; j++) {
            inicializar_individuo(&poblacion[i][j]);
            if((i == 0 && j == 0) || (evaluar(&poblacion[i][j]) > mejor_fitness_local)) {
                copiar(&mejor_individuo_local, &poblacion[i][j]);
                mejor_fitness_local = evaluar(&poblacion[i][j]);
            }
        }
    }

    // Definir vecinos para la migración (Anillo)
    int vecino_dest = (myrank + 1) % size;
    int vecino_origen = (myrank - 1 + size) % size;

    // Bucle principal
    for (int gen = 0; gen < GEN_MAX; gen++) {
        
        // --- ALGORITMO GENÉTICO ESTÁNDAR (Local) ---
        mejor_fitness_local = 0;
        int peor_fitness_local = L + 1;
        int peor_i = 0, peor_j = 0;

        for (i = 0; i < N_ROWS; i++) {
            for (j = 0; j < N_COLS; j++) {

                // Localizar al mejor y peor (para la migración posterior)
                if (poblacion[i][j].fitness > mejor_fitness_local) {
                    mejor_fitness_local = poblacion[i][j].fitness;
                    copiar(&mejor_individuo_local, &poblacion[i][j]);
                }
                if (poblacion[i][j].fitness < peor_fitness_local) {
                    peor_fitness_local = poblacion[i][j].fitness;
                    peor_i = i; peor_j = j;
                }

                // Selección, Crossover, Mutación
                int fc[4];
                vecino_aleatorios(i, j, fc); // Lógica original

                Individuo *p1 = &poblacion[fc[0]][fc[1]];
                Individuo *p2 = &poblacion[fc[2]][fc[3]];

                crossover_1p(p1, p2, &hijo);
                mutar(&hijo);
                hijo.fitness = evaluar(&hijo);

                // Reemplazo elitista
                if (hijo.fitness > poblacion[i][j].fitness) {
                    copiar(&nueva_poblacion[i][j], &hijo);
                } else {
                    copiar(&nueva_poblacion[i][j], &poblacion[i][j]);
                }
            }
        }

        // Copiar nueva población
        for (i = 0; i < N_ROWS; i++)
            for (j = 0; j < N_COLS; j++)
                copiar(&poblacion[i][j], &nueva_poblacion[i][j]);


        // --- CAMBIO MPI: MIGRACIÓN (Cada X generaciones) ---
        //Esto sería lo nuevo no he añadidido nada más
        if (gen % MIG_INTERVAL == 0 && size > 1) {
            Individuo inmigrante;
            MPI_Status st;

            // Envío a mi vecino mi MEJOR individuo
            // Recibo del otro vecino su MEJOR individuo
            MPI_Sendrecv(&mejor_individuo_local, sizeof(Individuo), MPI_BYTE, vecino_dest, 10,
                         &inmigrante, sizeof(Individuo), MPI_BYTE, vecino_origen, 10,
                         MPI_COMM_WORLD, &st);

            // Política de Inmigración:
            // Si el inmigrante es mejor que mi PEOR individuo, lo reemplazo.
            // Esto inyecta diversidad sin destruir lo bueno que ya tengo.
            if (inmigrante.fitness > poblacion[peor_i][peor_j].fitness) {
                copiar(&poblacion[peor_i][peor_j], &inmigrante);
                // Actualizar fitness local si por casualidad el inmigrante es buenísimo
                if (inmigrante.fitness > mejor_fitness_local) {
                     mejor_fitness_local = inmigrante.fitness;
                }
            }
        }


        // --- CAMBIO MPI: SINCRONIZACIÓN DE ESTADÍSTICAS ---
        // Necesitamos saber si ALGUIEN ha terminado.
        // MPI_Allreduce coge el MAX de los 'mejor_fitness_local' de todas las islas
        MPI_Allreduce(&mejor_fitness_local, &mejor_fitness_global_sistema, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);

        // Solo rank 0 imprime para mantener el formato del script Python
        if (myrank == 0) {
            printf("Generación %d | Mejor fitness: %d\n", gen, mejor_fitness_global_sistema);
        }

        // Condición de parada global
        if (mejor_fitness_global_sistema == L) break;
    }

    // Resultado final
    if (myrank == 0) {
        printf("\n=== RESULTADO FINAL ===\n");
        printf("Mejor fitness encontrado: %d\nMejor fitness posible: %d\n", mejor_fitness_global_sistema, L);
    }

    for(i = 0; i < N_ROWS; ++i) {
        free(poblacion[i]);
        free(nueva_poblacion[i]);
    }
    free(poblacion);
    free(nueva_poblacion);

    MPI_Finalize();
    return 0;
}