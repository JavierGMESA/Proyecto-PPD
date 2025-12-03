#ifndef HYBRID_TRUCK_EVALUATOR_H
#define HYBRID_TRUCK_EVALUATOR_H

#include <vector>
#include <string>

// Estructura de resultados visible para el alumno
struct EvaluationResult {
    double green_kms;
    double total_emissions; // kg CO2
    std::vector<bool> corrected_solution; // La solución tras ser reparada (si aplica)
    bool was_repaired;
};

// Forward declaration para ocultar detalles internos de structs si quisieras (opcional),
// pero aquí mantendremos los miembros privados visibles en el header pero inaccesibles.
struct Section; 
struct Truck;

class HybridTruckEvaluator {
public:
    // Constructor: Carga la ruta automáticamente.
    // El valor por defecto es el que indicaste.
    HybridTruckEvaluator(std::string filename = "SEG_Cad_Desp_Mad.csv");
    
    // Destructor
    ~HybridTruckEvaluator();

    // Función principal: El alumno entrega su vector de booleanos y recibe el resultado
    EvaluationResult evaluate(const std::vector<bool>& solution);

    // Auxiliar: Para que el alumno sepa cuántos bits debe tener su solución
    int getRouteSize() const;

private:
    // Lógica interna (Los alumnos ven esto pero NO pueden usarlo ni ver su código)
    std::vector<Section> route_sections;
    Truck* truck; // Usamos puntero para poder declararlo aquí sin exponer struct Truck completo si usamos forward decl
    bool take_stops;
    double slope_percent_limit;
    std::vector<double> l_segments_kwh_base;

    // Métodos internos privados
    void load_route(const std::string& filename);
    void init_truck();
    
    // Estructuras internas para retornos intermedios
    struct SectionResult;
    struct SimpleEvalResult;

    double vehicle_specific_power(double v, double slope, double acc, double m, double A);
    double decrease_battery_charge(double remaining, double section, double max);
    SectionResult section_power(double vo, double vf, double acc, double slope, double dist, double max_p, double m, double A);
    SimpleEvalResult simple_evaluate(const std::vector<bool>& sol);
    std::pair<std::vector<bool>, SimpleEvalResult> easy_repair_solution(std::vector<bool> sol, const std::vector<double>& charges);
};

#endif