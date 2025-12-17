#include "truck_mpi.hpp"
#include <cstdint>

// Mantiene misma firma/estructura, pero envía 1 byte por gen
Individuo* MPI_Comunicacion(const Individuo* mejor, const unsigned num_ejecuciones)
{
    const int tam = (int)mejor->genes.size();  // nº de genes

    // 1 byte por gen
    std::uint8_t* matriz_genes = new std::uint8_t[num_ejecuciones * tam];
    std::uint8_t* send_buf     = new std::uint8_t[tam];

    if (!matriz_genes || !send_buf) {
        fprintf(stderr, "Error reservando memoria en MPI_Comunicacion\n");
        delete[] matriz_genes;
        delete[] send_buf;
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    for (int i = 0; i < tam; ++i)
        send_buf[i] = mejor->genes[i] ? (std::uint8_t)1 : (std::uint8_t)0;

    // Cada proceso envía tam bytes (1 byte por gen)
    MPI_Allgather(
        (void*)send_buf,
        tam,
        MPI_UNSIGNED_CHAR,      // <- clave
        matriz_genes,
        tam,
        MPI_UNSIGNED_CHAR,
        MPI_COMM_WORLD
    );

    // Root difunde a todos
    //MPI_Bcast(
    //    matriz_genes,
    //    (int)(num_ejecuciones * tam),
    //    MPI_UNSIGNED_CHAR,      // <- clave
    //    0,
    //    MPI_COMM_WORLD
    //);

    Individuo* mejores = new Individuo[num_ejecuciones];
    if (!mejores) {
        fprintf(stderr, "Error reservando memoria para mejores\n");
        delete[] matriz_genes;
        delete[] send_buf;
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    for (unsigned r = 0; r < num_ejecuciones; ++r) {
        mejores[r].genes.clear();
        mejores[r].genes.reserve(tam);

        const std::uint8_t* row = matriz_genes + (size_t)r * tam;
        for (int i = 0; i < tam; ++i)
            mejores[r].genes.push_back(row[i] != 0);

        mejores[r].fitness = evaluar(&mejores[r]);
    }

    delete[] matriz_genes;
    delete[] send_buf;
    return mejores; // caller: delete[] mejores
}
