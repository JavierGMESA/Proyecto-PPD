//#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <omp.h>
#include "cga_param.h"

// Con openMP la rejilla se divide en subrejillas
// Con MPI cada proceso ejecuta su cga, y cada cierto tiempo se comparten individuos (seguramente el mejor de cada isla)
// que se introducen en posiciones aleatorias de la nueva población

typedef struct {
    int genes[L];
    int fitness;
} Individuo;

// ----------- FUNCIONES AUXILIARES -----------
int rand_int(int min, int max) {
    return min + rand() % (max - min + 1);
}

int rand_int_r(int min, int max, unsigned *semilla) {
    return min + rand_r(semilla) % (max - min + 1);
}

float rand_float_r(unsigned *semilla) {
    return (float) rand_r(semilla) / RAND_MAX;
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
    for (int i = 0; i < L; i++)
        dest->genes[i] = src->genes[i];
    dest->fitness = src->fitness;
}

// Crossover de 1 punto
void crossover_1p_r(const Individuo *p1, const Individuo *p2, Individuo *hijo, unsigned *semilla) {
    int punto = rand_int_r(1, L - 1, semilla);
    for (int i = 0; i < L; i++) {
        hijo->genes[i] = (i < punto) ? p1->genes[i] : p2->genes[i];
    }
}

// Mutación (10% de probabilidad de invertir un bit al azar)
void mutar_r(Individuo *ind, unsigned *semilla) {
    if ((rand_float_r(semilla)) < MUT_PROB) {
        int pos = rand_int_r(0, L - 1, semilla);
        ind->genes[pos] = 1 - ind->genes[pos];
    }
}

// Obtener índice de vecino (von Neumann)
void vecino_aleatorios(int fila, int col, int *fc, unsigned *semilla) {
    // fc[0], fc[1] -> primer vecino
    // fc[2], fc[3] -> segundo vecino

    // Movimientos posibles (arriba, abajo, izquierda, derecha)
    int df[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};

    for (int k = 0; k < 2; k++) {
        int nf, nc;
        do {
            int dir = rand_r(semilla) % 4;
            nf = fila + df[dir];
            nc = col + dc[dir];
        } while (nf < 0 || nf >= N_ROWS || nc < 0 || nc >= N_COLS);

        fc[k * 2]     = nf;
        fc[k * 2 + 1] = nc;
    }
}

// ------------------ PROGRAMA PRINCIPAL ------------------

int main() {
    srand(time(NULL));

    //Individuo poblacion[N_ROWS][N_COLS];
    //Individuo nueva_poblacion[N_ROWS][N_COLS];
    Individuo **poblacion, **nueva_poblacion;
    poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    nueva_poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    if(!poblacion || !nueva_poblacion)
    {
        printf("Ha habido error en la reserva de memoria");
        return 1;
    }
    int i, j;
    int fc[4];
    Individuo *p1, *p2;

    for(i = 0; i < N_ROWS; ++i)
    {
        poblacion[i] = (Individuo*) calloc (N_COLS, sizeof(Individuo));
        nueva_poblacion[i] = (Individuo*) calloc (N_COLS, sizeof(Individuo));
        if(!poblacion[i] || !nueva_poblacion[i])
        {
            printf("Ha habido error en la reserva de memoria");
            return 1;
        }
    }
    Individuo hijo, mejor_individuo;
    int mejor_fitness_global = 0;

    // Inicializar población
    for (i = 0; i < N_ROWS; i++)
        for (int j = 0; j < N_COLS; j++)
        {
            inicializar_individuo(&poblacion[i][j]);
            if((i == 0 && j == 0) || (evaluar(&poblacion[i][j]) > mejor_fitness_global))
            {
                copiar(&mejor_individuo, &poblacion[i][j]);
                mejor_fitness_global = evaluar(&poblacion[i][j]);
            }
        }
    
    unsigned seed_array[128];
    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        seed_array[tid] = rand();   // semillas bien separadas
    }
            

    // Bucle principal
    for (int gen = 0; gen < GEN_MAX; gen++) {
        #pragma omp parallel for shared(poblacion, nueva_poblacion, mejor_fitness_global) private(i, j, fc, p1, p2, hijo)
        for (i = 0; i < N_ROWS; i++) 
        {
            for (j = 0; j < N_COLS; j++) 
            {
                //unsigned int semilla = time(NULL) ^ (i * N_COLS + j) ^ omp_get_thread_num();
                int tid = omp_get_thread_num();
                unsigned* semilla;
                semilla = &seed_array[tid];   // cada hilo su propia semilla

                // Selección de dos padres vecinos
                vecino_aleatorios(i, j, fc, semilla);
                p1 = &poblacion[fc[0]][fc[1]];
                p2 = &poblacion[fc[2]][fc[3]];
                // Crossover + mutación
                crossover_1p_r(p1, p2, &hijo, semilla);
                mutar_r(&hijo, semilla);
                hijo.fitness = evaluar(&hijo);
                
                // Reemplazo elitista
                if (hijo.fitness > poblacion[i][j].fitness)
                {
                    copiar(&nueva_poblacion[i][j], &hijo);
                    #pragma omp critical
                    {
                        if(hijo.fitness > mejor_fitness_global)
                        {
                            copiar(&mejor_individuo, &hijo);
                            mejor_fitness_global = hijo.fitness;
                        }
                    }
                }  
                else
                    copiar(&nueva_poblacion[i][j], &poblacion[i][j]);
            }
        }

        // Copiar nueva población a actual
        for (int i = 0; i < N_ROWS; i++)
            for (int j = 0; j < N_COLS; j++)
                copiar(&poblacion[i][j], &nueva_poblacion[i][j]);

        printf("Generación %d | Mejor fitness: %d\n", gen, mejor_fitness_global);
    }

    // Resultado final
    printf("\n=== RESULTADO FINAL ===\n");
    printf("Mejor fitness encontrado: %d\nMejor fitness posible: %d\n", mejor_fitness_global, L);
    /*
    printf("Mejor individuo: ");
    for (int i = 0; i < L; i++)
        printf("%d", mejor_individuo.genes[i]);
    printf("\n");
    */

    for(i = 0; i < N_ROWS; ++i)
    {
        free(poblacion[i]);
        free(nueva_poblacion[i]);
    }
    free(poblacion);
    free(nueva_poblacion);


    return 0;
}
