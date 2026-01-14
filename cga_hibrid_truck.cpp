#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <omp.h>
#include "cga_param.h"
#include "truck.hpp"
#include "truck_mpi.hpp"

// ------------------ PROGRAMA PRINCIPAL ------------------

int main(int argc, char *argv[]) 
{
    if (argc < 3) 
    {
        printf("Uso: %s seed numThreads\n", argv[0]);
        printf("El número de parámetros pasados ha sido: %i", argc);
        return 1;
    }

    unsigned int seed = (unsigned int) strtoul(argv[1], NULL, 10);
    int num_threads   = atoi(argv[2]);
    omp_set_num_threads(num_threads);

    Individuo **poblacion, **nueva_poblacion;
    int i, j;
    int fc[4];
    Individuo *p1, *p2;
    Individuo hijo, mejor_individuo;
    double mejor_fitness_global = 0;

    double mejor_fitness, peor_fitness, suma_fitness;
    double mejor_green_kms, peor_green_kms, suma_green_kms;
    double mejor_emissions, peor_emissions, suma_emissions;

    int myrank, size;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    srand(seed + myrank);

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
        for (int j = 0; j < N_COLS; j++)
        {
            inicializar_individuo(&poblacion[i][j]);
            if((i == 0 && j == 0) || mejor_fitness_f(evaluar(&poblacion[i][j]), mejor_fitness_global))
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
        #pragma omp parallel for shared(poblacion, nueva_poblacion, mejor_fitness_global) private(i, j, fc, p1, p2, hijo) schedule(guided)
        for (i = 0; i < N_ROWS; i++) 
        {
            for (j = 0; j < N_COLS; j++) 
            {
                //unsigned int semilla = time(NULL) ^ (i * N_COLS + j) ^ omp_get_thread_num();
                int tid = omp_get_thread_num();
                unsigned* semilla;
                semilla = &seed_array[tid];   // cada hilo su propia semilla

                // Selección de dos padres vecinos
                vecino_aleatorios_r(i, j, fc, semilla);
                p1 = &poblacion[fc[0]][fc[1]];
                p2 = &poblacion[fc[2]][fc[3]];
                // Crossover + mutación
                crossover_1p_r(p1, p2, &hijo, semilla);
                mutar_r(&hijo, semilla);
                hijo.fitness = evaluar(&hijo);
                
                // Reemplazo elitista
                if (mejor_fitness_f(hijo.fitness, poblacion[i][j].fitness))
                {
                    copiar(&nueva_poblacion[i][j], &hijo);
                    #pragma omp critical
                    {
                        if(mejor_fitness_f(hijo.fitness, mejor_fitness_global))
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
        if((gen > 0 && gen % (GEN_MAX / 20) == 0) || gen == GEN_MAX - 1)
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
            delete[]mejores;
        }

        if(myrank == 0)
        {
            mejor_green_kms = suma_green_kms = 0.0;
            peor_green_kms = MAX_GREEN_KMS;
            mejor_emissions = MAX_TOTAL_EMISIONS;
            peor_emissions = suma_emissions = 0.0;
            mejor_fitness = suma_fitness = 0.0;
            peor_fitness = 2.0;
            for(i = 0; i < N_ROWS; ++i)
            {
                for(j = 0; j < N_COLS; ++j)
                {
                    suma_fitness += nueva_poblacion[i][j].fitness;
                    if(mejor_fitness_f(nueva_poblacion[i][j].fitness, mejor_fitness))
                    {
                        mejor_fitness = nueva_poblacion[i][j].fitness;
                    }
                    else if(mejor_fitness_f(peor_fitness, nueva_poblacion[i][j].fitness))
                    {
                        peor_fitness = nueva_poblacion[i][j].fitness;
                    }

                    suma_green_kms += nueva_poblacion[i][j].green_kms;
                    if(mejor_green_kms_f(nueva_poblacion[i][j].green_kms, mejor_green_kms))
                    {
                        mejor_green_kms = nueva_poblacion[i][j].green_kms;
                    }
                    else if(mejor_green_kms_f(peor_green_kms, nueva_poblacion[i][j].green_kms))
                    {
                        peor_green_kms = nueva_poblacion[i][j].green_kms;
                    }

                    suma_emissions += nueva_poblacion[i][j].total_emissions;
                    if(mejor_total_emissions_f(nueva_poblacion[i][j].total_emissions, mejor_emissions))
                    {
                        mejor_emissions = nueva_poblacion[i][j].total_emissions;
                    }
                    else if(mejor_total_emissions_f(peor_emissions, nueva_poblacion[i][j].total_emissions))
                    {
                        peor_emissions = nueva_poblacion[i][j].total_emissions;
                    }
                }
            }
        }

        // Copiar nueva población a actual
        for (int i = 0; i < N_ROWS; i++)
            for (int j = 0; j < N_COLS; j++)
                copiar(&poblacion[i][j], &nueva_poblacion[i][j]);

        if(myrank == 0)
        {
            printf("Generación %d\nMejor fitness global: %.6f\n", gen, mejor_fitness_global);
            printf("Mejor fitness: %.6f | Peor fitness: %.6f | Promedio de fitness: %.6f\n", mejor_fitness, peor_fitness, suma_fitness / (N_ROWS*N_COLS));
            printf("Mejor green kms: %.6f | Peor green kms: %.6f | Promedio de green kms: %.6f\n", mejor_green_kms, peor_green_kms, suma_green_kms / (N_ROWS*N_COLS));
            printf("Mejor emissions: %.6f | Peor emissions: %.6f | Promedio de emissions: %.6f\n", mejor_emissions, peor_emissions, suma_emissions / (N_ROWS*N_COLS));
        }
    }

    // Resultado final
    if(myrank == 0)
    {
        printf("\n=== RESULTADO FINAL ===\n");
        printf("Mejor fitness encontrado: %f\nMejor fitness posible: %f\n", mejor_fitness_global, 2.0);
    }

    for(i = 0; i < N_ROWS; ++i)
    {
        delete[] poblacion[i];
        delete[] nueva_poblacion[i];
    }
    //free(poblacion);
    //free(nueva_poblacion);
    delete[] poblacion;
    delete[] nueva_poblacion;

    MPI_Finalize();

    destroy_truck_evaluator();
    return 0;
}
