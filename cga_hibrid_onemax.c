#include <mpi.h>
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

float rand_float(unsigned *semilla) {
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
void crossover_1p(const Individuo *p1, const Individuo *p2, Individuo *hijo, unsigned *semilla) {
    int punto = rand_int_r(1, L - 1, semilla);
    for (int i = 0; i < L; i++) {
        hijo->genes[i] = (i < punto) ? p1->genes[i] : p2->genes[i];
    }
}

// Mutación (10% de probabilidad de invertir un bit al azar)
void mutar(Individuo *ind, unsigned *semilla) {
    if ((rand_float(semilla)) < MUT_PROB) {
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

Individuo* MPI_Comunicacion(const Individuo* mejor, const unsigned num_ejecuciones)
{
    // Matriz de genes: num_ejecuciones filas, L columnas
    // Se reserva en todos para poder hacer el Bcast después
    int *matriz_genes = (int*) malloc(num_ejecuciones * L * sizeof(int));
    if (!matriz_genes) {
        fprintf(stderr, "Error reservando memoria en MPI_Comunicacion\n");
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    // Cada proceso envía su mejor->genes (L ints).
    // En el root (0) se recibe la matriz con todos (num_ejecuciones x L).
    MPI_Gather(
        (void*)mejor->genes, // buffer de envío: L ints
        L,                   // número de ints que envía cada proceso
        MPI_INT,
        matriz_genes,        // solo se usa en root, pero debe existir en todos
        L,                   // número de ints que recibe de cada proceso
        MPI_INT,
        0,                   // root
        MPI_COMM_WORLD
    );

    // Root difunde la matriz completa a todos los procesos
    MPI_Bcast(matriz_genes, num_ejecuciones * L, MPI_INT, 0,MPI_COMM_WORLD);

    // Cada proceso crea un vector de Individuo a partir de la matriz
    Individuo *mejores = (Individuo*) malloc(num_ejecuciones * sizeof(Individuo));
    if (!mejores) {
        fprintf(stderr, "Error reservando memoria para mejores\n");
        free(matriz_genes);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    for (unsigned r = 0; r < num_ejecuciones; ++r) {
        // Copiar genes de la fila r
        for (int i = 0; i < L; ++i) {
            mejores[r].genes[i] = matriz_genes[r * L + i];
        }
        // Recalcular fitness (OneMax)
        mejores[r].fitness = evaluar(&mejores[r]);
    }

    free(matriz_genes);
    return mejores;   // El llamador hará free(mejores) cuando ya no lo necesite
}

// ------------------ PROGRAMA PRINCIPAL ------------------

int main(int argc, char *argv[]) {

    Individuo **poblacion, **nueva_poblacion;
    int i, j;
    int fc[4];
    Individuo *p1, *p2;
    Individuo hijo, mejor_individuo;
    int mejor_fitness_global = 0;

    int myrank, size, tag = 1;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    srand(time(NULL) + myrank);

    //Individuo poblacion[N_ROWS][N_COLS];
    //Individuo nueva_poblacion[N_ROWS][N_COLS];
    poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    nueva_poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    if(!poblacion || !nueva_poblacion)
    {
        printf("Ha habido error en la reserva de memoria");
        return 1;
    }

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
                crossover_1p(p1, p2, &hijo, semilla);
                mutar(&hijo, semilla);
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

        //Cada GEN_MAX / 20 generaciones introducimos los mejores individuos de cada isla en nuestra población
        //en posiciones aleatorias.
        if(gen > 0 && gen % (GEN_MAX / 20) == 0)
        {
            Individuo* mejores = MPI_Comunicacion(&mejor_individuo, size);
            for(int i2 = 0; i2 < size; ++i2)
            {
                int rand_row = rand_int(0, N_ROWS - 1);
                int rand_col = rand_int(0, N_COLS - 1);
                if(mejor_fitness_global < mejores[i2].fitness)
                {
                    copiar(&mejor_individuo, &mejores[i2]);
                    mejor_fitness_global = mejores[i2].fitness;
                }
                copiar(&nueva_poblacion[rand_row][rand_col], &mejores[i2]);
            }
            free(mejores);
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

    MPI_Finalize();
    return 0;
}
