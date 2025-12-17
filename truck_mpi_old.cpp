#include "truck_mpi.hpp"

Individuo* MPI_Comunicacion(const Individuo* mejor, const unsigned num_ejecuciones)
{
    // Matriz de genes: num_ejecuciones filas, L columnas
    // Se reserva en todos para poder hacer el Bcast después
    int tam = mejor->genes.size();
    int *matriz_genes = new int[num_ejecuciones * tam];
    int *send_buf = new int[tam];

    if (!matriz_genes || !send_buf) {
        fprintf(stderr, "Error reservando memoria en MPI_Comunicacion\n");
        delete[] matriz_genes;
        delete[] send_buf;
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    for(int i = 0; i < tam; ++i)
    {
        send_buf[i] = mejor->genes[i] ? 1 : 0;
    }

    // Cada proceso envía su mejor->genes (L ints).
    // En el root (0) se recibe la matriz con todos (num_ejecuciones x L).
    MPI_Gather(
        (void*)send_buf, // buffer de envío: L ints
        tam,                   // número de ints que envía cada proceso
        MPI_INT,
        matriz_genes,        // solo se usa en root, pero debe existir en todos
        tam,                   // número de ints que recibe de cada proceso
        MPI_INT,
        0,                   // root
        MPI_COMM_WORLD
    );

    // Root difunde la matriz completa a todos los procesos
    MPI_Bcast(matriz_genes, num_ejecuciones * tam, MPI_INT, 0,MPI_COMM_WORLD);

    // Cada proceso crea un vector de Individuo a partir de la matriz
    Individuo *mejores = new Individuo[num_ejecuciones];
    if (!mejores) {
        fprintf(stderr, "Error reservando memoria para mejores\n");
        delete[] matriz_genes;
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    for (unsigned r = 0; r < num_ejecuciones; ++r) {
        // Copiar genes de la fila r
        mejores[r].genes.clear();
        mejores[r].genes.reserve(tam);
        for (int i = 0; i < tam; ++i) {
            mejores[r].genes.push_back(matriz_genes[r * tam + i] != 0);
        }
        // Recalcular fitness
        mejores[r].fitness = evaluar(&mejores[r]);
    }

    delete[] matriz_genes;
    delete[] send_buf;
    return mejores;   // El llamador hará delete[] mejores cuando ya no lo necesite
}