#include "truck.hpp"
#include "cga_param.h"

// Evaluador global
static HybridTruckEvaluator* evaluator = nullptr;

static void init_truck_evaluator() 
{
    if (!evaluator) {
        evaluator = new HybridTruckEvaluator("SEG_Cad_Desp_Mad.csv");
    }
}

// ----------- FUNCIONES AUXILIARES -----------
int rand_int(int min, int max) {
    return min + rand() % (max - min + 1);
}

int rand_int_r(int min, int max, unsigned *semilla) {
    return min + rand_r(semilla) % (max - min + 1);
}

float rand_float() {
    return (float) rand() / RAND_MAX;
}

float rand_float_r(unsigned *semilla) {
    return (float) rand_r(semilla) / RAND_MAX;
}

double evaluar(Individuo *ind) {
    init_truck_evaluator();
    double s = 0;
    EvaluationResult res = evaluator->evaluate(ind->genes);
    s = res.green_kms / MAX_GREEN_KMS + (1 - res.total_emissions / MAX_TOTAL_EMISIONS);
    if(res.was_repaired)
    {
        ind->genes = res.corrected_solution;
        ind->fitness = s;
    }
    return s;
}

void inicializar_individuo(Individuo *ind) {
    init_truck_evaluator();
    int tam = evaluator->getRouteSize();
    ind->genes.clear();
    ind->genes.reserve(tam);
    for (int i = 0; i < tam; i++)
        ind->genes.push_back(rand_int(0, 1) == 0);;
    ind->fitness = evaluar(ind);
}

void copiar(Individuo *dest, const Individuo *src) {
    dest->genes = src->genes;
    dest->fitness = src->fitness;
}

void crossover_1p(const Individuo *p1, const Individuo *p2, Individuo *hijo) 
{
    int tam = p1->genes.size();
    int punto = rand_int(1, tam - 1);
    hijo->genes.clear();
    hijo->genes.reserve(tam);
    for (int i = 0; i < tam; i++) {
        //hijo->genes[i] = (i < punto) ? p1->genes[i] : p2->genes[i];
        hijo->genes.push_back((i < punto) ? p1->genes[i] : p2->genes[i]);
    }
}

void crossover_1p_r(const Individuo *p1, const Individuo *p2, Individuo *hijo, unsigned *semilla) 
{
    int tam = p1->genes.size();
    int punto = rand_int_r(1, tam - 1, semilla);
    hijo->genes.clear();
    hijo->genes.reserve(tam);
    for (int i = 0; i < tam; i++) 
    {
        //hijo->genes[i] = (i < punto) ? p1->genes[i] : p2->genes[i];
        hijo->genes.push_back((i < punto) ? p1->genes[i] : p2->genes[i]);
    }
}

short mutar(Individuo *ind) 
{
    int tam = ind->genes.size();
    if (rand_float() < MUT_PROB) 
    {
        int pos = rand_int(0, tam - 1);
        //ind->genes[pos] = 1 - ind->genes[pos];
        ind->genes[pos] = !ind->genes[pos]; 
        return 1;
    }
    else 
    {
        return 0;
    }
}

short mutar_r(Individuo *ind, unsigned *semilla) 
{
    int tam = ind->genes.size();
    if (rand_float_r(semilla) < MUT_PROB) 
    {
        int pos = rand_int_r(0, tam - 1, semilla);
        //ind->genes[pos] = 1 - ind->genes[pos];
        ind->genes[pos] = !ind->genes[pos]; 
        return 1;
    }
    else 
    {
        return 0;
    }
}

void vecino_aleatorios(int fila, int col, int *fc) {
    // fc[0], fc[1] -> primer vecino
    // fc[2], fc[3] -> segundo vecino

    // Movimientos posibles (arriba, abajo, izquierda, derecha)
    int df[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};

    for (int k = 0; k < 2; k++) {
        int nf, nc;
        do {
            int dir = rand() % 4;
            nf = fila + df[dir];
            nc = col + dc[dir];
        } while (nf < 0 || nf >= N_ROWS || nc < 0 || nc >= N_COLS);

        fc[k * 2]     = nf;
        fc[k * 2 + 1] = nc;
    }
}

void vecino_aleatorios_r(int fila, int col, int *fc, unsigned *semilla) {
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

short mejor_fitness_f(double posible_mejor_fitness, double posible_peor_fitness)
{
    return posible_mejor_fitness > posible_peor_fitness;
}

int Izhikevich(float *v, float *u, float a, float b, float c, float d, float I)
{
    float dt = 1.0f;  // paso de tiempo
    *v += dt * (0.04f * (*v) * (*v) + 5.0f * (*v) + 140.0f - (*u) + I);
    *u += dt * (a * (b * (*v) - (*u)));

    //Limites para evitar el Nan (Not a number)
    if (*v < -200.0f) *v = -200.0f;
    if (*v > 200.0f) *v = 200.0f;

    if(*v > 30)
    {
        *v = c;
        *u = (*u) + d;
        return 1;
    }
    else 
    {
        return 0;
    }
}

void Izhikevich_limitar_parametros(float *b, float *c, float *d, float *I)
{
    if (*I < 0) *I = 0;
    if (*I > 20) *I = 20;

    if (*b < 0.05) *b = 0.05;
    if (*b > 0.3)  *b = 0.3;

    if (*c < -80)  *c = -80;
    if (*c > -30)  *c = -30;

    if (*d < 0)    *d = 0;
    if (*d > 8)    *d = 8;
}

void destroy_truck_evaluator() {
    if (evaluator) {
        delete evaluator;
        evaluator = nullptr;
    }
}