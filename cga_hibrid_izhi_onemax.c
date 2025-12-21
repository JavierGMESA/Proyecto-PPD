#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <omp.h>
#include "cga_param.h"
#include "onemax.h"
#include "onemax_mpi.h"

//Variables para Izhikevich
float IniI, IncMutI, IncPosI, IncNegI, IncPicI;
float IniA;
float IniB, IncPosB, IncNegB, IncPicB;
float IniC, IncPosC, IncNegC, IncPicC;
float IniD, IncPosD, IncNegD, IncPicD;
int MAX_ULT_PICO, MAX_PIC_SEG;

// ------------------ PROGRAMA PRINCIPAL ------------------

int main(int argc, char *argv[]) {

    if (argc != 23) 
    {
        printf("Uso: %s seed numThreads IniI IncMutI IncPosI IncNegI IncPicI IniA IniB IncPosB IncNegB IncPicB IniC IncPosC IncNegC IncPicC IniD IncPosD IncNegD IncPicD MAX_ULT_PICO MAX_PIC_SEG\n", argv[0]);
        printf("El número de parámetros pasados ha sido: %i", argc);
        return 1;
    }

    unsigned int seed = (unsigned int) strtoul(argv[1], NULL, 10);
    int num_threads   = atoi(argv[2]);
    omp_set_num_threads(num_threads);

    int idx = 3;
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

    Individuo **poblacion, **nueva_poblacion;
    Individuo hijo, mejor_individuo;
    Individuo *p1, *p2;
    int mejor_fitness_global = 0;

    int mejor_fitness, peor_fitness, suma_fitness;

    int i, j;
    int fc[4];
    float v, u;
    float a = IniA, b = IniB, c = IniC, d = IniD, I = IniI;
    v = c;
    u = b * v;
    short hay_mutacion, hay_pico;
    long total_picos = 0;
    int ultimo_pico = 0, picos_seguidos = 0, umbral_f_bajo = 1, umbral_f_alto = 2;

    int myrank, size;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    srand(seed + myrank);

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
        for (j = 0; j < N_COLS; j++)
        {
            inicializar_individuo(&poblacion[i][j]);
            if((i == 0 && j == 0) || mejor_fitness_f(evaluar(&poblacion[i][j]), mejor_fitness_global))
            {
                copiar(&mejor_individuo, &poblacion[i][j]);
                mejor_fitness_global = evaluar(&poblacion[i][j]);
            }
        }
    
    unsigned seed_array[128];
    float b_p[128], c_p[128], d_p[128], I_p[128], v_p[128], u_p[128];
    int ultimo_pico_p[128], picos_seguidos_p[128];
    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        seed_array[tid] = rand();   // semillas bien separadas

        b_p[tid] = b;
        c_p[tid] = c;
        d_p[tid] = d;
        I_p[tid] = I;
        ultimo_pico_p[tid] = ultimo_pico;
        picos_seguidos_p[tid] = picos_seguidos;
        v_p[tid] = v;
        u_p[tid] = u;
    }

    // Bucle principal
    for (int gen = 0; gen < GEN_MAX; gen++) 
    {
        total_picos = 0;
        #pragma omp parallel for shared(a, poblacion, nueva_poblacion, mejor_fitness_global) private(i, j, fc, p1, p2, hijo, hay_pico, hay_mutacion) default(shared)
        for (i = 0; i < N_ROWS; i++) 
        {
            for (j = 0; j < N_COLS; j++) 
            {
                // CREAR SEMILLA LOCAL PARA rand_r (Crucial para que funcione en paralelo)
                // Combinamos tiempo, coordenadas e ID del hilo para que sea única
                int tid = omp_get_thread_num();
                unsigned* semilla;
                semilla = &seed_array[tid];   // cada hilo su propia semilla

                // Selección de dos padres vecinos
                vecino_aleatorios_r(i, j, fc, semilla);
                p1 = &poblacion[fc[0]][fc[1]];
                p2 = &poblacion[fc[2]][fc[3]];

                // Crossover + mutación
                crossover_1p_r(p1, p2, &hijo, semilla);
                hay_mutacion = mutar_r(&hijo, semilla);

                if(hay_mutacion)
                {
                    I_p[tid] += IncMutI;
                }

                hijo.fitness = evaluar(&hijo);

                if(hijo.fitness - poblacion[i][j].fitness < umbral_f_bajo)
                {
                    I_p[tid] += IncPosI;
                    b_p[tid] += IncPosB;
                    c_p[tid] += IncPosC;
                    d_p[tid] += IncPosD;
                }

                if(hijo.fitness - poblacion[i][j].fitness > umbral_f_alto)
                {
                    I_p[tid] += IncNegI;
                    b_p[tid] += IncNegB;
                    c_p[tid] += IncNegC;
                    d_p[tid] += IncNegD;
                }

                Izhikevich_limitar_parametros(&b_p[tid], &c_p[tid], &d_p[tid], &I_p[tid]);


                hay_pico = Izhikevich(&v_p[tid], &u_p[tid], a, b_p[tid], c_p[tid], d_p[tid], I_p[tid]);

                if(hay_pico)
                {
                    //printf("Ha habido pico\n");
                    ultimo_pico_p[tid] = 0;
                    ++picos_seguidos_p[tid];
                    #pragma omp critical
                    {
                        ++total_picos;
                    }
                }
                else 
                {
                    if(picos_seguidos_p[tid] > 0)
                    {
                        ++ultimo_pico_p[tid];
                        if(ultimo_pico_p[tid] > MAX_ULT_PICO)
                        {
                            ultimo_pico_p[tid] = 0;
                            picos_seguidos_p[tid] = 0;
                        }
                    }
                }

                if(picos_seguidos_p[tid] > MAX_PIC_SEG)
                {
                    I_p[tid] += IncPicI;
                    b_p[tid] += IncPicB;
                    c_p[tid] += IncPicC;
                    d_p[tid] += IncPicD;
                    --picos_seguidos_p[tid];
                }

                Izhikevich_limitar_parametros(&b_p[tid], &c_p[tid], &d_p[tid], &I_p[tid]);
                // Fuga dependiente del nivel de excitación
                if (picos_seguidos_p[tid] > 5)
                    I_p[tid] *= 0.9f;
                else
                    I_p[tid] *= 0.98f;

                // Reemplazo elitista
                if(hay_pico || mejor_fitness_f(hijo.fitness, poblacion[i][j].fitness))
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
            free(mejores);
        }

        if(myrank == 0)
        {
            mejor_fitness = suma_fitness = 0;
            peor_fitness = L;
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
                }
            }
        }

        // Copiar nueva población a actual
        for (int i = 0; i < N_ROWS; i++)
            for (int j = 0; j < N_COLS; j++)
                copiar(&poblacion[i][j], &nueva_poblacion[i][j]);

        if(myrank == 0)
        {
            printf("Generación %d\nMejor fitness global: %d | Picos presentados: %ld\n", gen, mejor_fitness_global, total_picos);
            printf("Mejor fitness: %d | Peor fitness: %d | Promedio de fitness: %d\n", mejor_fitness, peor_fitness, suma_fitness / (N_ROWS*N_COLS));
        }
    }

    if(myrank == 0)
    {
        // Resultado final
        printf("\n=== RESULTADO FINAL ===\n");
        printf("Mejor fitness encontrado: %d\nMejor fitness posible: %d\n", mejor_fitness_global, L);
    }

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