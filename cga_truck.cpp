#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "cga_param.h"
#include "truck.hpp"

// ------------------ PROGRAMA PRINCIPAL ------------------

int main() {
    srand(time(NULL));

    Individuo **poblacion, **nueva_poblacion;
    //poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    //nueva_poblacion = (Individuo**) calloc(N_ROWS, sizeof(Individuo*));
    poblacion = new Individuo*[N_ROWS];
    nueva_poblacion = new Individuo*[N_ROWS];                   //CAMBIO
    if(!poblacion || !nueva_poblacion)
    {
        printf("Ha habido error en la reserva de memoria");
        return 1;
    }
    int i;
    for(i = 0; i < N_ROWS; ++i)
    {
        //poblacion[i] = (Individuo*) calloc (N_COLS, sizeof(Individuo));
        //nueva_poblacion[i] = (Individuo*) calloc (N_COLS, sizeof(Individuo));
        poblacion[i] = new Individuo[N_COLS];
        nueva_poblacion[i] = new Individuo[N_COLS];             //CAMBIO
        if(!poblacion[i] || !nueva_poblacion[i])
        {
            printf("Ha habido error en la reserva de memoria");
            return 1;
        }
    }

    Individuo hijo, mejor_individuo;
    double mejor_fitness_global = 0;            //CAMBIO

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
            

    // Bucle principal
    for (int gen = 0; gen < GEN_MAX; gen++) {
        for (i = 0; i < N_ROWS; i++) {
            for (int j = 0; j < N_COLS; j++) {

                // Selección de dos padres vecinos
                int fc[4];
                vecino_aleatorios(i, j, fc);

                Individuo *p1 = &poblacion[fc[0]][fc[1]];
                Individuo *p2 = &poblacion[fc[2]][fc[3]];

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

        // Copiar nueva población a actual
        for (int i = 0; i < N_ROWS; i++)
            for (int j = 0; j < N_COLS; j++)
                copiar(&poblacion[i][j], &nueva_poblacion[i][j]);

        printf("Generación %d | Mejor fitness: %f\n", gen, mejor_fitness_global);                       //CAMBIO
    }

    // Resultado final
    printf("\n=== RESULTADO FINAL ===\n");
    printf("Mejor fitness encontrado: %f\nMejor fitness posible: %f\n", mejor_fitness_global, 2.0);     //CAMBIO

    for(i = 0; i < N_ROWS; ++i)
    {
        delete[] poblacion[i];
        delete[] nueva_poblacion[i];                //CAMBIO
    }
    delete[] poblacion;
    delete[] nueva_poblacion;                       //CAMBIO

    return 0;
}
