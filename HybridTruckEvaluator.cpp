#include "HybridTruckEvaluator.h"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <fstream>
#include <sstream>
#include <map>
#include <numeric>

const double G_GRAVITY = 9.80665;
const double CR_ROLLING_RES = 0.006;
const double CD_DRAG_COEF = 0.63;
const double RO_AIR = 1.225;

struct Section {
    int identity;
    double speed;
    double slope;
    double slope_percent;
    double distance;
    double seconds;
    double acceleration;
    int stop_start;
};

struct Truck {
    double ICE_power;
    double EV_power;
    double charge;
    double weight;
    double frontal_section;
    double fuel_engine_efficiency;
    double electric_engine_efficiency;
};

struct HybridTruckEvaluator::SectionResult {
    double final_speed;
    double final_acc;
    double kwh_consumed;
    double bat_regen;
};

struct HybridTruckEvaluator::SimpleEvalResult {
    double total_emissions;
    double green_kms;
    std::vector<double> remaining_charges;
    bool is_valid;
};

HybridTruckEvaluator::HybridTruckEvaluator(std::string filename) {
    truck = new Truck();
    init_truck();
    take_stops = true;
    slope_percent_limit = -1.5;
    
    load_route(filename);

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

std::vector<std::string> parse_csv_row_internal(const std::string& line) {
    std::vector<std::string> result;
    std::string cell;
    bool inside_quotes = false;
    for (char c : line) {
        if (c == '"') {
            inside_quotes = !inside_quotes;
        } else if (c == ',' && !inside_quotes) {
            result.push_back(cell);
            cell.clear();
        } else {
            cell += c;
        }
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
        for (size_t i = 0; i < headers.size(); ++i) {
            header_map[headers[i]] = i;
        }
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
        } catch (...) {
            continue;
        }
    }
}

double HybridTruckEvaluator::vehicle_specific_power(double v, double slope, double acc, double m, double A) {
    double aux_energy = 2.0; 
    double n_dc = 0.90;
    double n_m = 0.95;
    double n_t = 0.96;
    double n_b = 0.97;
    double n_g = 0.90;

    double Frff = G_GRAVITY * CR_ROLLING_RES * m * std::cos(slope);
    double Fadf = RO_AIR * A * CD_DRAG_COEF * std::pow(v, 2) / 2.0;
    double Fhcf = G_GRAVITY * m * std::sin(slope);
    double Farf = m * acc;
    double Fttf = Frff + Fadf + Fhcf + Farf; 

    double power = (Fttf * v) / 1000.0; 
    double rbf = 1.0 - std::exp(-v * 0.36); 
    double total_power = 0.0;

    if (power < 0) {
        double total_n = n_dc * n_g * n_t * n_b;
        total_power = aux_energy / n_b + rbf * power * total_n;
    } else {
        double total_n = n_dc * n_m * n_t * n_b;
        total_power = aux_energy / n_b + power / total_n;
    }
    return total_power;
}

double HybridTruckEvaluator::decrease_battery_charge(double remaining_charge, double section_charge, double truck_max_charge) {
    if ((remaining_charge - section_charge) > truck_max_charge) {
        return truck_max_charge;
    } else {
        return remaining_charge - section_charge;
    }
}

HybridTruckEvaluator::SectionResult HybridTruckEvaluator::section_power(double vo, double vf_target, double acc_in, double slope, 
                            double section_distance_km, double max_engine_power, 
                            double m, double A) {
    double acc = acc_in;
    double vf = vf_target;
    double section_distance_m = section_distance_km * 1000.0;
    
    double acc_decay = 0.2;
    double v_decay = 0.1;
    double instant_speed = vo;
    double total_power_accum = 0.0;
    
    double kW = vehicle_specific_power(vf, slope, acc, m, A);
    double vf_original = vf;
    
    if (kW > max_engine_power) {
        while (kW > max_engine_power) {
            vf -= v_decay;
            kW = vehicle_specific_power(vf, slope, 0.0, m, A);
        }
    }

    double remaining_distance = section_distance_m;
    double tot_secs = 0.0;
    double bat_regen = 0.0;
    std::vector<double> l_kw;
    bool signed_changed = true;

    if (vf >= vo) { 
        if (vf - 0.1 <= vo) acc = 0;
        if (acc <= 0) signed_changed = false;

        while (remaining_distance > 0 && instant_speed <= vf && (acc > 0 || !signed_changed)) {
            kW = vehicle_specific_power(instant_speed, slope, acc, m, A);
            
            if (kW < max_engine_power) {
                acc += acc_decay;
            }
            
            while (kW > max_engine_power) {
                acc -= acc_decay;
                kW = vehicle_specific_power(instant_speed, slope, acc, m, A);
            }
            
            while (kW < max_engine_power && vf < vf_original - 0.1) {
                vf = std::min(vf + v_decay * 0.5, vf_original);
                kW = vehicle_specific_power(instant_speed, slope, acc, m, A);
            }

            if (!signed_changed && acc > 0) signed_changed = true;

            if (acc != 0) {
                double acc_distance = (std::pow(instant_speed + acc, 2) - std::pow(instant_speed, 2)) / (2 * acc);
                remaining_distance -= acc_distance;
                instant_speed += acc;
                total_power_accum += kW;
                l_kw.push_back(kW);
            }
        }
    } else {
        if (vf >= instant_speed - 0.1) acc = 0;
        
        signed_changed = true;
        if (acc >= 0) signed_changed = false;

        while (remaining_distance > 0 && instant_speed >= vf && (acc < 0 || !signed_changed)) {
            kW = vehicle_specific_power(instant_speed, slope, acc, m, A);
            
            double speed_fraction = (vo != vf) ? (vo - instant_speed) / (vo - vf) : 1.0;

            if (speed_fraction < 0.5) {
                acc = std::max(-2.0, acc - acc_decay);
            } else {
                acc += acc_decay;
            }

            while (kW > max_engine_power) {
                acc -= acc_decay;
                kW = vehicle_specific_power(instant_speed, slope, acc, m, A);
            }

            if (!signed_changed && acc < 0) signed_changed = true;

            if (acc != 0) {
                double acc_distance = (std::pow(instant_speed + acc, 2) - std::pow(instant_speed, 2)) / (2 * acc);
                remaining_distance -= acc_distance;
                instant_speed += acc;
                total_power_accum += kW;
                l_kw.push_back(kW);
                tot_secs += 1.0;
            }
        }
        
        if (vo > vf && l_kw.size() > 1 && (l_kw.front() - l_kw.back() < 0)) {
            bat_regen = (l_kw.front() - l_kw.back()) * tot_secs / 3600.0;
        }
    }

    if (remaining_distance > 0) {
        double t_remaining = (instant_speed > 0) ? remaining_distance / instant_speed : 0;
        kW = vehicle_specific_power(instant_speed, slope, 0, m, A);
        total_power_accum += t_remaining * kW;
        tot_secs += t_remaining;
    }

    return {instant_speed, acc, total_power_accum / 3600.0, bat_regen};
}

HybridTruckEvaluator::SimpleEvalResult HybridTruckEvaluator::simple_evaluate(const std::vector<bool>& solution_vec) {
    double total_emissions = 0.0;
    double green_kms = 0.0;
    double remaining_charge = truck->charge;
    std::vector<double> remaining_charges;
    
    double current_speed = 0.0;
    double acc = 0.0;
    bool invalid = false;

    for (size_t i = 0; i < route_sections.size(); ++i) {
        const auto& section = route_sections[i];
        bool is_electric = solution_vec[i];
        
        if (section.stop_start == 1 && (take_stops || i == 0)) {
            current_speed = 0.0;
        }

        double max_power = is_electric ? truck->EV_power : truck->ICE_power;

        SectionResult res = section_power(current_speed, section.speed, acc, 
                                            section.slope, section.distance, 
                                            max_power, truck->weight, truck->frontal_section);
        
        current_speed = res.final_speed;
        acc = res.final_acc;

        double section_emissions = 0.0;

        if (res.kwh_consumed < 0) {
                remaining_charge = decrease_battery_charge(remaining_charge, res.kwh_consumed / truck->electric_engine_efficiency, truck->charge);
        } else {
            remaining_charge = decrease_battery_charge(remaining_charge, res.bat_regen / truck->electric_engine_efficiency, truck->charge);
            
            if (is_electric) {
                remaining_charge = decrease_battery_charge(remaining_charge, res.kwh_consumed / truck->electric_engine_efficiency, truck->charge);
                green_kms += section.distance;
            } else {
                double gasoline_gallon_equivalent = res.kwh_consumed / truck->fuel_engine_efficiency * 0.02635046113;
                section_emissions += gasoline_gallon_equivalent * 10.180;
                total_emissions += section_emissions;
            }
        }

        if (remaining_charge < 0) invalid = true;
        remaining_charges.push_back(remaining_charge);

        if ((i + 1) >= route_sections.size() || (route_sections[i+1].stop_start == 1 && take_stops)) {
            remaining_charge = truck->charge;
        }
    }

    return {total_emissions, green_kms, remaining_charges, !invalid};
}

std::pair<std::vector<bool>, HybridTruckEvaluator::SimpleEvalResult> HybridTruckEvaluator::easy_repair_solution(std::vector<bool> solution, const std::vector<double>& remaining_charges) {
    std::vector<int> electric_indices;
    for(size_t i=0; i<solution.size(); ++i) {
        if(solution[i]) electric_indices.push_back(i);
    }

    std::sort(electric_indices.begin(), electric_indices.end(), [&](int a, int b) {
        return l_segments_kwh_base[a] < l_segments_kwh_base[b];
    });

    int curr_eliminar = electric_indices.size() - 1;
    bool still_negative = true;
    SimpleEvalResult current_eval; 

    while(still_negative && curr_eliminar >= 0) {
        int idx_to_flip = electric_indices[curr_eliminar];
        solution[idx_to_flip] = false; 

        current_eval = simple_evaluate(solution);
        
        still_negative = !current_eval.is_valid;
        curr_eliminar--;
    }

    return {solution, current_eval};
}

EvaluationResult HybridTruckEvaluator::evaluate(const std::vector<bool>& input_solution) {
    if (input_solution.size() != route_sections.size()) {
        std::cerr << "[Error] El tamaño de la solucion (" << input_solution.size() 
                  << ") no coincide con la ruta (" << route_sections.size() << ")." << std::endl;
        return {0.0, 0.0, input_solution, false};
    }

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