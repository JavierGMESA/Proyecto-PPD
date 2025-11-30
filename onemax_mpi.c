#include "onemax_mpi.h"

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