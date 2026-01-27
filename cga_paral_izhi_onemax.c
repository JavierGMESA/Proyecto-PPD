#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <omp.h>
#include "cga_param.h"
#include "onemax.h"

//Variables para Izhikevich
float IniI, IncMutI, IncPosI, IncNegI, IncPicI;
float IniA;
float IniB, IncPosB, IncNegB, IncPicB;
float IniC, IncPosC, IncNegC, IncPicC;
float IniD, IncPosD, IncNegD, IncPicD;
int MAX_ULT_PICO, MAX_PIC_SEG;

// ------------------ PROGRAMA PRINCIPAL ------------------

int main(int argc, char *argv[]) 
{
    if (argc != 23) 
    {
        printf("Uso: %s seed numThreads IniI IncMutI IncPosI IncNegI IncPicI IniA IniB IncPosB IncNegB IncPicB IniC IncPosC IncNegC IncPicC IniD IncPosD IncNegD IncPicD MAX_ULT_PICO MAX_PIC_SEG\n", argv[0]);
        printf("El número de parámetros pasados ha sido: %i", argc);
        return 1;
    }

    //Asignación de variables de entrada
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

    //Declaración de variables
    Individuo **poblacion, **nueva_poblacion;
    Individuo *p1, *p2;
    Individuo hijo, mejor_individuo;
    int mejor_fitness_global = 0;
    int mejor_fitness, peor_fitness, suma_fitness;
    float v, u;
    float a = IniA, b = IniB, c = IniC, d = IniD, I = IniI;
    v = c;
    u = b * v;
    short hay_mutacion, hay_pico;
    long total_picos = 0;
    int ultimo_pico = 0, picos_seguidos = 0, umbral_f_bajo = 1, umbral_f_alto = 2;
    int i, j;
    int fc[4];

    //Programa principal
    srand(seed);

    //Creación de población inicial
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

    //Inicialización de neuronas de cada hilo
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
            

    //Bucle principal
    for (int gen = 0; gen < GEN_MAX; gen++) 
    {
        total_picos = 0;
        #pragma omp parallel for shared(a, poblacion, nueva_poblacion, mejor_fitness_global) private(i, j, fc, p1, p2, hijo, hay_pico, hay_mutacion) default(shared)
        for (i = 0; i < N_ROWS; i++) 
        {
            for (j = 0; j < N_COLS; j++) 
            {   
                //Crear semilla con rand_r (crucial para que funcione en paralelo)
                int tid = omp_get_thread_num();
                unsigned* semilla;
                semilla = &seed_array[tid];   // cada hilo su propia semilla

                //Selección de dos padres vecinos
                vecino_aleatorios_r(i, j, fc, semilla);
                p1 = &poblacion[fc[0]][fc[1]];
                p2 = &poblacion[fc[2]][fc[3]];

                //Crossover + mutación
                crossover_1p_r(p1, p2, &hijo, semilla);
                hay_mutacion = mutar_r(&hijo, semilla);

                //Izhikevich: si hay mutacion cambia la I
                if(hay_mutacion)
                {
                    I_p[tid] += IncMutI;
                }

                //Obtenemos el fitness del hijo
                hijo.fitness = evaluar(&hijo);

                //Izhikevich: Si la diferencia de fitness es menor que el umbral inferior cambio en las variables
                if(hijo.fitness - poblacion[i][j].fitness < umbral_f_bajo)
                {
                    I_p[tid] += IncPosI;
                    b_p[tid] += IncPosB;
                    c_p[tid] += IncPosC;
                    d_p[tid] += IncPosD;
                }

                //Izhikevich: Si la diferencia de fitness es mayor que el umbral superior cambio en las variables
                if(hijo.fitness - poblacion[i][j].fitness > umbral_f_alto)
                {
                    I_p[tid] += IncNegI;
                    b_p[tid] += IncNegB;
                    c_p[tid] += IncNegC;
                    d_p[tid] += IncNegD;
                }

                //Limitamos los parámetros para evitar errores
                Izhikevich_limitar_parametros(&b_p[tid], &c_p[tid], &d_p[tid], &I_p[tid]);

                hay_pico = Izhikevich(&v_p[tid], &u_p[tid], a, b_p[tid], c_p[tid], d_p[tid], I_p[tid]);

                //Llevamos la cuenta del nº de picos
                if(hay_pico)
                {
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

                //Izhikevich: si hay muchos picos seguidos se cambian las variables
                if(picos_seguidos_p[tid] > MAX_PIC_SEG)
                {
                    I_p[tid] += IncPicI;
                    b_p[tid] += IncPicB;
                    c_p[tid] += IncPicC;
                    d_p[tid] += IncPicD;
                    --picos_seguidos_p[tid];
                }

                Izhikevich_limitar_parametros(&b_p[tid], &c_p[tid], &d_p[tid], &I_p[tid]);
                //Fuga dependiente del nivel de excitación
                if (picos_seguidos_p[tid] > 5)
                    I_p[tid] *= 0.9f;
                else
                    I_p[tid] *= 0.98f;

                //Reemplazo con Izhikevich
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

        //Llevamos la cuenta del mejor, peor y promedio de fitness
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

        //Copiar nueva población a actual
        for (int i = 0; i < N_ROWS; i++)
            for (int j = 0; j < N_COLS; j++)
                copiar(&poblacion[i][j], &nueva_poblacion[i][j]);

        printf("Generación %d\nMejor fitness global: %d | Picos presentados: %ld\n", gen, mejor_fitness_global, total_picos);
        printf("Mejor fitness: %d | Peor fitness: %d | Promedio de fitness: %d\n", mejor_fitness, peor_fitness, suma_fitness / (N_ROWS*N_COLS));
    }

    //Resultado final
    printf("\n=== RESULTADO FINAL ===\n");
    printf("Mejor fitness encontrado: %d\nMejor fitness posible: %d\n", mejor_fitness_global, L);

    //Liberamos la memoria
    for(i = 0; i < N_ROWS; ++i)
    {
        free(poblacion[i]);
        free(nueva_poblacion[i]);
    }
    free(poblacion);
    free(nueva_poblacion);

    return 0;
}