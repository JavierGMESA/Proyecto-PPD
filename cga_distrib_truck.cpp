#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "cga_param.h"
#include "truck.hpp"
#include "truck_mpi.hpp"

// ------------------ PROGRAMA PRINCIPAL ------------------

int main(int argc, char *argv[]) 
{
    //Individuo poblacion[N_ROWS][N_COLS];
    //Individuo nueva_poblacion[N_ROWS][N_COLS];
    Individuo **poblacion, **nueva_poblacion;
    int i, j;
    int fc[4];
    Individuo *p1, *p2;
    Individuo hijo, mejor_individuo;
    double mejor_fitness_global = 0;

    int myrank, size;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    srand(time(NULL) + myrank);

    //poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    //nueva_poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    poblacion = new Individuo*[N_ROWS];
    nueva_poblacion = new Individuo*[N_ROWS];
    if(!poblacion || !nueva_poblacion)
    {
        printf("Ha habido error en la reserva de memoria");
        return 1;
    }
    
    for(i = 0; i < N_ROWS; ++i)
    {
        //poblacion[i] = (Individuo*) calloc (N_COLS, sizeof(Individuo));
        //nueva_poblacion[i] = (Individuo*) calloc (N_COLS, sizeof(Individuo));
        poblacion[i] = new Individuo[N_COLS];
        nueva_poblacion[i] = new Individuo[N_COLS];
        if(!poblacion[i] || !nueva_poblacion[i])
        {
            printf("Ha habido error en la reserva de memoria");
            return 1;
        }
    }

    // Inicializar población
    for (i = 0; i < N_ROWS; i++)
        for (j = 0; j < N_COLS; j++)
        {
            inicializar_individuo(&poblacion[i][j]);
            if((i == 0 && j == 0) || mejor_fitness_f(evaluar(&poblacion[i][j]), mejor_fitness_global))
            {
                copiar(&mejor_individuo, &poblacion[i][j]);
                mejor_fitness_global = evaluar(&poblacion[i][j]);
            }
        }
            

    // Bucle principal
    for (int gen = 0; gen < GEN_MAX; gen++) {
        for (i = 0; i < N_ROWS; i++) {
            for (int j = 0; j < N_COLS; j++) {

                // Selección de dos padres vecinos
                vecino_aleatorios(i, j, fc);

                p1 = &poblacion[fc[0]][fc[1]];
                p2 = &poblacion[fc[2]][fc[3]];

                // Crossover + mutación
                crossover_1p(p1, p2, &hijo);
                mutar(&hijo);
                hijo.fitness = evaluar(&hijo);

                    // Reemplazo elitista
                if (mejor_fitness_f(hijo.fitness, poblacion[i][j].fitness))
                {
                    copiar(&nueva_poblacion[i][j], &hijo);
                    if(mejor_fitness_f(hijo.fitness, mejor_fitness_global))
                    {
                        copiar(&mejor_individuo, &hijo);
                        mejor_fitness_global = hijo.fitness;
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
                if(mejor_fitness_f(mejores[i2].fitness, mejor_fitness_global))
                {
                    copiar(&mejor_individuo, &mejores[i2]);
                    mejor_fitness_global = mejores[i2].fitness;
                }
                copiar(&nueva_poblacion[rand_row][rand_col], &mejores[i2]);
            }
            delete[] mejores;
        }

        // Copiar nueva población a actual
        for (int i = 0; i < N_ROWS; i++)
            for (int j = 0; j < N_COLS; j++)
                copiar(&poblacion[i][j], &nueva_poblacion[i][j]);

        if(myrank == 0)
        {
            printf("Generación %d | Mejor fitness: %f\n", gen, mejor_fitness_global);
        }
    }

    if(myrank == 0)
    {
        // Resultado final
        printf("\n=== RESULTADO FINAL ===\n");
        printf("Mejor fitness encontrado: %f\nMejor fitness posible: %f\n", mejor_fitness_global, 2.0);
    }

    for(i = 0; i < N_ROWS; ++i)
    {
        //free(poblacion[i]);
        //free(nueva_poblacion[i]);
        delete[] poblacion[i];
        delete[] nueva_poblacion[i];
    }
    //free(poblacion);
    //free(nueva_poblacion);
    delete[] poblacion;
    delete[] nueva_poblacion;


    MPI_Finalize();
    return 0;
}
