#ifndef ONEMAX
#define ONEMAX

#include <stdlib.h>
#include <fstream>
#include <time.h>
#include <stdio.h>
#include <vector>
#include "cga_param.h"
#include "HybridTruckEvaluator.h"

typedef struct {
    std::vector<bool> genes;
    double fitness, green_kms, total_emissions;
} Individuo;

// ----------- FUNCIONES AUXILIARES -----------
int rand_int(int min, int max);

int rand_int_r(int min, int max, unsigned *semilla);

float rand_float();

float rand_float_r(unsigned *semilla);

// Evaluar OneMax
double evaluar(Individuo *ind);

// Inicializar individuo aleatorio
void inicializar_individuo(Individuo *ind);

// Copiar individuo
void copiar(Individuo *dest, const Individuo *src);

// Crossover de 1 punto
void crossover_1p(const Individuo *p1, const Individuo *p2, Individuo *hijo);

void crossover_1p_r(const Individuo *p1, const Individuo *p2, Individuo *hijo, unsigned *semilla);

// Mutación (10% de probabilidad de invertir un bit al azar)
short mutar(Individuo *ind);

short mutar_r(Individuo *ind, unsigned *semilla);

// Obtener índice de vecino (von Neumann)
void vecino_aleatorios(int fila, int col, int *fc);

void vecino_aleatorios_r(int fila, int col, int *fc, unsigned *semilla);

// Comparar fitness
short mejor_fitness_f(double posible_mejor_fitness, double posible_peor_fitness);

//Comparar kilometros verdes
short mejor_green_kms_f(double posible_mejor_green_kms, double posible_peor_green_kms);

//Comparar emisiones totales
short mejor_total_emissions_f(double posible_mejor_total_emissions, double posible_peor_total_emissions);

//Actualizar 'v' y 'u' de Izhikevich
int Izhikevich(float *v, float *u, float a, float b, float c, float d, float I);

void Izhikevich_limitar_parametros(float *b, float *c, float *d, float *I);

void destroy_truck_evaluator();

void dump_poblacion_truck(const char *filename, int generacion, Individuo **poblacion);

#endif