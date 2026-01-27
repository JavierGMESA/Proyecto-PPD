#include <stdio.h>
#include <stdlib.h>
#include <time.h>
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
    int mejor_fitness_global = 0;
    int mejor_fitness, peor_fitness, suma_fitness;
    float v, u;
    float a = IniA, b = IniB, c = IniC, d = IniD, I = IniI;
    v = c;
    u = b * v;
    short hay_mutacion, hay_pico;
    long total_picos = 0;
    int ultimo_pico = 0, picos_seguidos = 0, umbral_f_bajo = 1, umbral_f_alto = 2;

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
    int i, j;
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
        for (j = 0; j < N_COLS; j++)
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
                int fc[4];
                vecino_aleatorios(i, j, fc);
                Individuo *p1 = &poblacion[fc[0]][fc[1]];
                Individuo *p2 = &poblacion[fc[2]][fc[3]];

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