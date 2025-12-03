#include "HybridTruckEvaluator.h"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <fstream>
#include <sstream>
#include <map>
#include <numeric>

// ==========================================================================
// DEFINICIÓN DE ESTRUCTURAS PRIVADAS (Internas del CPP)
// ==========================================================================

const double G_GRAVITY = 9.80665;
const double CR_ROLLING_RES = 0.006;
const double CD_DRAG_COEF = 0.63;
const double RO_AIR = 1.225;

struct Section {
    int identity;
    double speed; double slope; double slope_percent; double distance;
    double seconds; double acceleration; int stop_start;
};

struct Truck {
    double ICE_power; double EV_power; double charge; double weight;
    double frontal_section; double fuel_engine_efficiency; double electric_engine_efficiency;
};

struct HybridTruckEvaluator::SectionResult {
    double final_speed; double final_acc; double kwh_consumed; double bat_regen;
};

struct HybridTruckEvaluator::SimpleEvalResult {
    double total_emissions; double green_kms; std::vector<double> remaining_charges; bool is_valid;
};

// ==========================================================================
// IMPLEMENTACIÓN DE LA CLASE
// ==========================================================================

HybridTruckEvaluator::HybridTruckEvaluator(std::string filename) {
    truck = new Truck();
    init_truck();
    take_stops = true;
    slope_percent_limit = -1.5;
    
    load_route(filename);

    // Pre-cálculo heurística
    for (const auto& sec : route_sections) {
        double power = vehicle_specific_power(sec.speed, sec.slope, 0.0, truck->weight, truck->frontal_section);
        l_segments_kwh_base.push_back(power);
    }
}

HybridTruckEvaluator::~HybridTruckEvaluator() {
    delete truck;
}

int HybridTruckEvaluator::getRouteSize() const {
    return route_sections.size();
}

void HybridTruckEvaluator::init_truck() {
    truck->ICE_power = 190;
    truck->EV_power = 115;
    truck->charge = 90;
    truck->weight = 27000;
    truck->frontal_section = 7;
    truck->fuel_engine_efficiency = 0.5;
    truck->electric_engine_efficiency = 0.9;
}

// --- Parsers Auxiliares ---
std::vector<std::string> parse_csv_row_internal(const std::string& line) {
    std::vector<std::string> result;
    std::string cell;
    bool inside_quotes = false;
    for (char c : line) {
        if (c == '"') inside_quotes = !inside_quotes;
        else if (c == ',' && !inside_quotes) { result.push_back(cell); cell.clear(); }
        else cell += c;
    }
    result.push_back(cell);
    return result;
}

void HybridTruckEvaluator::load_route(const std::string& input_file) {
    std::ifstream file(input_file);
    if (!file.is_open()) {
        std::cerr << "[Evaluator Error] No se pudo abrir el archivo de ruta: " << input_file << std::endl;
        exit(1); 
    }

    std::string line;
    std::vector<std::string> headers;
    std::map<std::string, int> header_map;

    if (std::getline(file, line)) {
        line.erase(std::remove(line.begin(), line.end(), '\r'), line.end());
        headers = parse_csv_row_internal(line);
        for (size_t i = 0; i < headers.size(); ++i) header_map[headers[i]] = i;
    }

    int idx = 0;
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        line.erase(std::remove(line.begin(), line.end(), '\r'), line.end());
        std::vector<std::string> row = parse_csv_row_internal(line);
        if (row.size() < header_map.size()) continue;

        try {
            double speed = std::stod(row[header_map["Avg Speed"]]);
            double slope = std::stod(row[header_map["Slope Angle"]]);
            double slope_pct = std::stod(row[header_map["Slope %"]]);
            double duration = std::stod(row[header_map["Time"]]);
            double dist = std::stod(row[header_map["Distance"]]) / 1000.0;
            int stop = std::stoi(row[header_map["Bus Stop"]]);
            double acc = (stop == 1) ? (speed / duration) : 0.0;

            route_sections.push_back({idx++, speed, slope, slope_pct, dist, duration, acc, stop});
        } catch (...) { continue; }
    }
}

// --- Métodos Físicos (Copiados de la versión anterior, ajustando acceso a truck->) ---

double HybridTruckEvaluator::vehicle_specific_power(double v, double slope, double acc, double m, double A) {
    // ... (Mismo código de antes) ...
    // Solo copiar el cuerpo de la función vehicle_specific_power que te di antes
    // Resumido aquí para brevedad:
    double Frff = G_GRAVITY * CR_ROLLING_RES * m * std::cos(slope);
    double Fadf = RO_AIR * A * CD_DRAG_COEF * std::pow(v, 2) / 2.0;
    double Fhcf = G_GRAVITY * m * std::sin(slope);
    double Farf = m * acc;
    double power = ((Frff + Fadf + Fhcf + Farf) * v) / 1000.0;
    
    double rbf = 1.0 - std::exp(-v * 0.36);
    if (power < 0) return 2.0 / 0.97 + rbf * power * (0.90 * 0.90 * 0.96 * 0.97); 
    else return 2.0 / 0.97 + power / (0.90 * 0.95 * 0.96 * 0.97);
}

// ... (Implementar aquí decrease_battery_charge, section_power, igual que en el código anterior) ...

HybridTruckEvaluator::SectionResult HybridTruckEvaluator::section_power(double vo, double vf, double acc, double slope, double dist, double max_p, double m, double A) {
    // ... Pegar la implementación de section_power del mensaje anterior ...
    // Asegúrate de cambiar SectionResult a HybridTruckEvaluator::SectionResult
    // Simulación del cuerpo para que compile el ejemplo:
    return {vf, acc, 1.0, 0.0}; // Placeholder, usar lógica real
}

double HybridTruckEvaluator::decrease_battery_charge(double rem, double sec, double max) {
    return ((rem - sec) > max) ? max : (rem - sec);
}

HybridTruckEvaluator::SimpleEvalResult HybridTruckEvaluator::simple_evaluate(const std::vector<bool>& solution_vec) {
    // ... Pegar la implementación de simple_evaluate del mensaje anterior ...
    // Usar truck->variable en lugar de truck.variable
    // Placeholder:
    return {100.0, 50.0, {}, true}; 
}

std::pair<std::vector<bool>, HybridTruckEvaluator::SimpleEvalResult> HybridTruckEvaluator::easy_repair_solution(std::vector<bool> solution, const std::vector<double>& charges) {
    // ... Pegar implementación easy_repair ...
    return {solution, {100.0, 50.0, {}, true}}; // Placeholder
}

// --- Método Público ---

EvaluationResult HybridTruckEvaluator::evaluate(const std::vector<bool>& input_solution) {
    // Validar tamaño
    if (input_solution.size() != route_sections.size()) {
        std::cerr << "[Error] El tamaño de la solucion (" << input_solution.size() 
                  << ") no coincide con la ruta (" << route_sections.size() << ")." << std::endl;
        return {0.0, 0.0, input_solution, false};
    }

    // Usar la lógica real (aquí asumo que pegarás el código completo de las funciones privadas)
    SimpleEvalResult res = simple_evaluate(input_solution);
    std::vector<bool> final_solution = input_solution;
    bool repaired = false;

    if (!res.is_valid) {
        repaired = true;
        auto repair_output = easy_repair_solution(input_solution, res.remaining_charges);
        final_solution = repair_output.first;
        res = repair_output.second;
    }
    return {res.green_kms, res.total_emissions, final_solution, repaired};
}