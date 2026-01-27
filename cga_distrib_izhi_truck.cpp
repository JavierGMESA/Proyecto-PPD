#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "cga_param.h"
#include "truck.hpp"
#include "truck_mpi.hpp"

//Variables para Izhikevich
float IniI, IncMutI, IncPosI, IncNegI, IncPicI;
float IniA;
float IniB, IncPosB, IncNegB, IncPicB;
float IniC, IncPosC, IncNegC, IncPicC;
float IniD, IncPosD, IncNegD, IncPicD;
int MAX_ULT_PICO, MAX_PIC_SEG;

// ------------------ PROGRAMA PRINCIPAL ------------------

int main(int argc, char *argv[]) {

    if (argc != 22) 
    {
        printf("Uso: %s seed IniI IncMutI IncPosI IncNegI IncPicI IniA IniB IncPosB IncNegB IncPicB IniC IncPosC IncNegC IncPicC IniD IncPosD IncNegD IncPicD MAX_ULT_PICO MAX_PIC_SEG\n", argv[0]);
        printf("El número de parámetros pasados ha sido: %i", argc);
        return 1;
    }

    //Asignación de variables de entrada
    unsigned int seed = (unsigned int) strtoul(argv[1], NULL, 10);

    int idx = 2;
    IniI     = atof(argv[idx++]);
    IncMutI  = atof(argv[idx++]);
    IncPosI  = atof(argv[idx++]);
    IncNegI  = atof(argv[idx++]);
    IncPicI  = atof(argv[idx++]);

    IniA     = atof(argv[idx++]);

    IniB     = atof(argv[idx++]);
    IncPosB  = atof(argv[idx++]);
    IncNegB  = atof(argv[idx++]);
    IncPicB  = atof(argv[idx++]);

    IniC     = atof(argv[idx++]);
    IncPosC  = atof(argv[idx++]);
    IncNegC  = atof(argv[idx++]);
    IncPicC  = atof(argv[idx++]);

    IniD     = atof(argv[idx++]);
    IncPosD  = atof(argv[idx++]);
    IncNegD  = atof(argv[idx++]);
    IncPicD  = atof(argv[idx++]);

    MAX_ULT_PICO = atoi(argv[idx++]);
    MAX_PIC_SEG  = atoi(argv[idx++]);

    //Declaración de variables
    Individuo **poblacion, **nueva_poblacion;
    Individuo hijo, mejor_individuo;
    Individuo *p1, *p2;
    double mejor_fitness_global = 0;
    int i, j;
    int fc[4];
    float v, u;
    float a = IniA, b = IniB, c = IniC, d = IniD, I = IniI;
    v = c;
    u = b * v;
    short hay_mutacion, hay_pico;
    long total_picos = 0;
    int ultimo_pico = 0, picos_seguidos = 0;
    float umbral_f_bajo = 0.001, umbral_f_alto = 0.08;

    double mejor_fitness, peor_fitness, suma_fitness;
    double mejor_green_kms, peor_green_kms, suma_green_kms;
    double mejor_emissions, peor_emissions, suma_emissions;

    int myrank, size;

    //Programa principal
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    srand(seed + myrank);

    //Creación de población inicial
    poblacion = new Individuo*[N_ROWS];
    nueva_poblacion = new Individuo*[N_ROWS];
    if(!poblacion || !nueva_poblacion)
    {
        printf("Ha habido error en la reserva de memoria");
        return 1;
    }
    for(i = 0; i < N_ROWS; ++i)
    {
        poblacion[i] = new Individuo[N_COLS];
        nueva_poblacion[i] = new Individuo[N_COLS];
        if(!poblacion[i] || !nueva_poblacion[i])
        {
            printf("Ha habido error en la reserva de memoria");
            return 1;
        }
    }

    //Inicializar población
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
            

    //Bucle principal
    for (int gen = 0; gen < GEN_MAX; gen++) 
    {
        total_picos = 0;
        for (i = 0; i < N_ROWS; i++) 
        {
            for (j = 0; j < N_COLS; j++) 
            {

                //Selección de dos padres vecinos
                vecino_aleatorios(i, j, fc);
                p1 = &poblacion[fc[0]][fc[1]];
                p2 = &poblacion[fc[2]][fc[3]];

                //Crossover + mutación
                crossover_1p(p1, p2, &hijo);
                hay_mutacion = mutar(&hijo);

                //Izhikevich: si hay mutacion cambia la I
                if(hay_mutacion)
                {
                    I += IncMutI;
                }

                //Obtenemos el fitness del hijo
                hijo.fitness = evaluar(&hijo);

                //Izhikevich: Si la diferencia de fitness es menor que el umbral inferior cambio en las variables
                if(hijo.fitness - poblacion[i][j].fitness < umbral_f_bajo)
                {
                    I += IncPosI;
                    b += IncPosB;
                    c += IncPosC;
                    d += IncPosD;
                }

                //Izhikevich: Si la diferencia de fitness es mayor que el umbral superior cambio en las variables
                if(hijo.fitness - poblacion[i][j].fitness > umbral_f_alto)
                {
                    I += IncNegI;
                    b += IncNegB;
                    c += IncNegC;
                    d += IncNegD;
                }

                //Limitamos los parámetros para evitar errores
                Izhikevich_limitar_parametros(&b, &c, &d, &I);

                hay_pico = Izhikevich(&v, &u, a, b, c, d, I);

                //Llevamos la cuenta del nº de picos
                if(hay_pico)
                {
                    ultimo_pico = 0;
                    ++picos_seguidos;
                    ++total_picos;
                }
                else 
                {
                    if(picos_seguidos > 0)
                    {
                        ++ultimo_pico;
                        if(ultimo_pico > MAX_ULT_PICO)
                        {
                            ultimo_pico = 0;
                            picos_seguidos = 0;
                        }
                    }
                }

                //Izhikevich: si hay muchos picos seguidos se cambian las variables
                if(picos_seguidos > MAX_PIC_SEG)
                {
                    I += IncPicI;
                    b += IncPicB;
                    c += IncPicC;
                    d += IncPicD;
                    --picos_seguidos;
                }

                Izhikevich_limitar_parametros(&b, &c, &d, &I);
                //Fuga dependiente del nivel de excitación
                if (picos_seguidos > 5)
                    I *= 0.9f;
                else
                    I *= 0.98f;

                //Reemplazo con Izhikevich
                if(hay_pico || mejor_fitness_f(hijo.fitness, poblacion[i][j].fitness))
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

        //Llevamos la cuenta del mejor, peor y promedio de fitness, kms verdes y CO2
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

        //Copiar nueva población a actual
        for (int i = 0; i < N_ROWS; i++)
            for (int j = 0; j < N_COLS; j++)
                copiar(&poblacion[i][j], &nueva_poblacion[i][j]);

        if(myrank == 0)
        {
            printf("Generación %d\nMejor fitness global: %.6f | Picos presentados: %ld\n", gen, mejor_fitness_global, total_picos);
            printf("Mejor fitness: %.6f | Peor fitness: %.6f | Promedio de fitness: %.6f\n", mejor_fitness, peor_fitness, suma_fitness / (N_ROWS*N_COLS));
            printf("Mejor green kms: %.6f | Peor green kms: %.6f | Promedio de green kms: %.6f\n", mejor_green_kms, peor_green_kms, suma_green_kms / (N_ROWS*N_COLS));
            printf("Mejor emissions: %.6f | Peor emissions: %.6f | Promedio de emissions: %.6f\n", mejor_emissions, peor_emissions, suma_emissions / (N_ROWS*N_COLS));
        }
    }

    if(myrank == 0)
    {
        //Resultado final
        printf("\n=== RESULTADO FINAL ===\n");
        printf("Mejor fitness encontrado: %f\nMejor fitness posible: %f\n", mejor_fitness_global, 2.0);
    }

    //Liberamos la memoria
    for(i = 0; i < N_ROWS; ++i)
    {
        delete[] poblacion[i];
        delete[] nueva_poblacion[i];
    }
    delete[] poblacion;
    delete[] nueva_poblacion;

    MPI_Finalize();

    destroy_truck_evaluator();

    return 0;
}