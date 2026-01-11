import random
import math
import copy
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass, field

# ============================================================================
# CONFIGURATION
# ============================================================================
WSTATION = 6
SIMULATION_TIME = 8.0

# Global worker ID counter (z in your description)
_WORKER_ID_COUNTER = 1

def get_next_worker_id() -> int:
    """Get the next worker ID and increment the counter"""
    global _WORKER_ID_COUNTER
    worker_id = _WORKER_ID_COUNTER
    _WORKER_ID_COUNTER += 1
    return worker_id

def reset_worker_id_counter():
    """Reset the worker ID counter (useful for testing)"""
    global _WORKER_ID_COUNTER
    _WORKER_ID_COUNTER = 1

# ============================================================================
# PHASE 1: CLASS DEFINITIONS
# ============================================================================

@dataclass
class TrueWorkerProfile:
    worker_id: str
    skill1: float
    skill2: float
    skill3: float
    skill4: float
    skill5: float
    skill6: float
    fatigue_base: float
    
    def get_skill(self, station: int) -> float:
        skills = [self.skill1, self.skill2, self.skill3, 
                  self.skill4, self.skill5, self.skill6]
        return skills[station - 1]
    
    def calculate_energy_avg(self, fatigue_cost: float, T: float = SIMULATION_TIME) -> float:
        k = fatigue_cost / (self.fatigue_base + 5)
        
        if k * T < 0.001:
            energy_avg = 1.0
        else:
            energy_avg = (1 - math.exp(-k * T)) / (k * T)
        
        return energy_avg
    
    def calculate_performance(self, station: int, task_delivery_time: float, 
                            task_fatigue_cost: float) -> float:
        skill = self.get_skill(station)
        energy_avg = self.calculate_energy_avg(task_fatigue_cost)
        performance = (skill / task_delivery_time) * energy_avg
        return performance
    
    def to_dict(self):
        return {
            'worker_id': self.worker_id,
            'skill1': self.skill1,
            'skill2': self.skill2,
            'skill3': self.skill3,
            'skill4': self.skill4,
            'skill5': self.skill5,
            'skill6': self.skill6,
            'fatigue_base': self.fatigue_base
        }


@dataclass
class FactoryWorkerProfile:
    worker_id: str
    performance_percentages: Dict[int, List[float]] = field(default_factory=dict)
    
    def record_performance_percentage(self, station: int, percentage: float):
        if station not in self.performance_percentages:
            self.performance_percentages[station] = []
        self.performance_percentages[station].append(percentage)
    
    def get_average_percentage(self, station: int) -> float:
        if station not in self.performance_percentages or not self.performance_percentages[station]:
            return 0.0
        return sum(self.performance_percentages[station]) / len(self.performance_percentages[station])
    
    def has_data_for_station(self, station: int) -> bool:
        return station in self.performance_percentages and len(self.performance_percentages[station]) > 0
    
    def get_data_completeness(self) -> float:
        stations_with_data = sum(1 for i in range(1, WSTATION + 1) 
                                if self.has_data_for_station(i))
        return (stations_with_data / WSTATION) * 100
    
    def to_dict(self):
        return {
            'worker_id': self.worker_id,
            'performance_percentages': {str(k): v for k, v in self.performance_percentages.items()},
            'data_completeness': self.get_data_completeness(),
            'avg_percentages': {s: self.get_average_percentage(s) for s in range(1, WSTATION + 1)}
        }


@dataclass
class TaskProfile:
    station_id: int
    delivery_time: float
    fatigue_cost: float
    
    def to_dict(self):
        return {
            'station_id': self.station_id,
            'delivery_time': self.delivery_time,
            'fatigue_cost': self.fatigue_cost
        }


def generate_true_worker() -> TrueWorkerProfile:
    """
    Generate a true worker using the global counter.
    """
    worker_id = get_next_worker_id()
    
    return TrueWorkerProfile(
        worker_id=f"{worker_id:04d}",
        skill1=random.uniform(1.0, 10.0),
        skill2=random.uniform(1.0, 10.0),
        skill3=random.uniform(1.0, 10.0),
        skill4=random.uniform(1.0, 10.0),
        skill5=random.uniform(1.0, 10.0),
        skill6=random.uniform(1.0, 10.0),
        fatigue_base=random.uniform(1.0, 10.0)
    )


def generate_task_profiles() -> List[TaskProfile]:
    tasks = []
    for station in range(1, WSTATION + 1):
        task = TaskProfile(
            station_id=station,
            delivery_time=random.uniform(2.0, 5.0),
            fatigue_cost=random.uniform(1.0, 10.0)
        )
        tasks.append(task)
    return tasks


def create_initial_assignment_sequential(worker_ids: List[str]) -> Dict[int, List[str]]:
    assignment = {station: [] for station in range(1, WSTATION + 1)}
    
    for idx, worker_id in enumerate(worker_ids):
        station = (idx % WSTATION) + 1
        assignment[station].append(worker_id)
    
    return assignment


def fire_worker_from_assignment(worker_id: str, assignment: Dict[int, List[str]]) -> Dict[int, List[str]]:
    """
    Remove worker and rebalance assignment to maintain sequential structure.
    """
    new_assignment = {station: [] for station in range(1, WSTATION + 1)}
    
    # Collect all remaining workers in order
    all_workers = []
    for station in range(1, WSTATION + 1):
        for wid in assignment[station]:
            if wid != worker_id:
                all_workers.append(wid)
    
    # Redistribute sequentially
    for idx, wid in enumerate(all_workers):
        station = (idx % WSTATION) + 1
        new_assignment[station].append(wid)
    
    return new_assignment


# ============================================================================
# PHASE 2: ENVIRONMENT SIMULATION
# ============================================================================

def simulate_station_performance(
    true_workers: List[TrueWorkerProfile],
    tasks: List[TaskProfile],
    assignment: Dict[int, List[str]]
) -> Dict[int, float]:
    true_worker_dict = {w.worker_id: w for w in true_workers}
    task_dict = {t.station_id: t for t in tasks}
    
    station_performance = {}
    
    for station_id, worker_ids in assignment.items():
        task = task_dict[station_id]
        total_performance = 0.0
        
        for worker_id in worker_ids:
            if worker_id in true_worker_dict:
                true_worker = true_worker_dict[worker_id]
                performance = true_worker.calculate_performance(
                    station_id,
                    task.delivery_time,
                    task.fatigue_cost
                )
                total_performance += performance
        
        station_performance[station_id] = total_performance
    
    return station_performance


# ============================================================================
# PHASE 3: SYSTEMATIC SWAPPING WITH REAL-TIME OPTIMIZATION
# ============================================================================

def optimize_position(
    factory_workers: List[FactoryWorkerProfile],
    current_assignment: Dict[int, List[str]],
    position_idx: int
) -> tuple[Dict[int, List[str]], Dict]:
    factory_worker_dict = {w.worker_id: w for w in factory_workers}
    optimized_assignment = copy.deepcopy(current_assignment)
    
    position_workers = []
    stations_with_position = []
    
    for station in range(1, WSTATION + 1):
        if position_idx < len(current_assignment[station]):
            worker_id = current_assignment[station][position_idx]
            position_workers.append(worker_id)
            stations_with_position.append(station)
    
    if not position_workers:
        return optimized_assignment, {}
    
    assigned_workers = set()
    optimization_details = {}
    
    for station in stations_with_position:
        best_worker = None
        best_score = -float('inf')
        
        for worker_id in position_workers:
            if worker_id not in assigned_workers:
                score = factory_worker_dict[worker_id].get_average_percentage(station)
                if score > best_score:
                    best_score = score
                    best_worker = worker_id
        
        if best_worker:
            old_worker = optimized_assignment[station][position_idx]
            optimized_assignment[station][position_idx] = best_worker
            assigned_workers.add(best_worker)
            
            optimization_details[station] = {
                'old_worker': old_worker,
                'new_worker': best_worker,
                'score': best_score
            }
    
    return optimized_assignment, optimization_details


def check_position_needs_testing(
    factory_workers: List[FactoryWorkerProfile],
    assignment: Dict[int, List[str]],
    position_idx: int
) -> bool:
    """Check if any worker at this position needs data collection"""
    factory_worker_dict = {w.worker_id: w for w in factory_workers}
    
    for station in range(1, WSTATION + 1):
        if position_idx < len(assignment[station]):
            worker_id = assignment[station][position_idx]
            if worker_id in factory_worker_dict:
                if factory_worker_dict[worker_id].get_data_completeness() < 100:
                    return True
    
    return False


def systematic_data_collection_ui(
    true_workers: List[TrueWorkerProfile],
    factory_workers: List[FactoryWorkerProfile],
    tasks: List[TaskProfile],
    initial_assign: Dict[int, List[str]],
    cycle_callback: Optional[Callable] = None
) -> Dict[int, List[str]]:
    
    base_performance = simulate_station_performance(true_workers, tasks, initial_assign)
    
    factory_worker_dict = {w.worker_id: w for w in factory_workers}
    for station_id, worker_ids in initial_assign.items():
        for worker_id in worker_ids:
            if worker_id in factory_worker_dict:
                factory_worker_dict[worker_id].record_performance_percentage(station_id, 100.0)
    
    if cycle_callback:
        cycle_callback({
            'cycle': 1,
            'phase': 'base',
            'assignment': copy.deepcopy(initial_assign),
            'base_performance': base_performance,
            'factory_workers': [w.to_dict() for w in factory_workers]
        })
    
    current_assignment = copy.deepcopy(initial_assign)
    original_assignment = copy.deepcopy(initial_assign)
    
    max_workers_per_station = max(len(workers) for workers in initial_assign.values())
    
    cycle = 2
    
    for position_idx in range(max_workers_per_station):
        # Skip if all workers at this position have complete data
        if not check_position_needs_testing(factory_workers, original_assignment, position_idx):
            if cycle_callback:
                cycle_callback({
                    'cycle': f'Skip_Pos_{position_idx + 1}',
                    'phase': 'skip',
                    'position_idx': position_idx,
                    'assignment': copy.deepcopy(current_assignment),
                    'message': f'Skipped position {position_idx + 1} - all workers have complete data'
                })
            continue
        
        workers_to_rotate = []
        source_stations = []
        for station in range(1, WSTATION + 1):
            if position_idx < len(original_assignment[station]):
                worker_id = original_assignment[station][position_idx]
                workers_to_rotate.append(worker_id)
                source_stations.append(station)
        
        if not workers_to_rotate:
            continue
        
        temp_assignment = copy.deepcopy(current_assignment)
        
        for rotation in range(len(workers_to_rotate)):
            rotated_workers = workers_to_rotate[rotation:] + workers_to_rotate[:rotation]
            
            for i, station in enumerate(source_stations):
                temp_assignment[station][position_idx] = rotated_workers[i]
            
            current_performance = simulate_station_performance(true_workers, tasks, temp_assignment)
            
            performance_comparison = {}
            for idx, station_id in enumerate(source_stations):
                base_perf = base_performance[station_id]
                curr_perf = current_performance[station_id]
                raw_percentage = (curr_perf / base_perf) * 100 if base_perf != 0 else 100.0
                
                swapped_worker = rotated_workers[idx]
                
                # Skip recording if worker already has data for this station
                if factory_worker_dict[swapped_worker].has_data_for_station(station_id):
                    continue
                
                adjustment = 0.0
                
                for pos, worker_id in enumerate(temp_assignment[station_id]):
                    if pos != position_idx:
                        if pos < len(original_assignment[station_id]):
                            original_worker_at_pos = original_assignment[station_id][pos]
                            if worker_id != original_worker_at_pos:
                                worker_perf = factory_worker_dict[worker_id].get_average_percentage(station_id)
                                adjustment += (worker_perf - 100.0)
                
                adjusted_percentage = raw_percentage - adjustment
                
                performance_comparison[station_id] = {
                    'raw_percentage': raw_percentage,
                    'adjusted_percentage': adjusted_percentage,
                    'worker': swapped_worker
                }
                
                factory_worker_dict[swapped_worker].record_performance_percentage(
                    station_id, adjusted_percentage
                )
            
            if cycle_callback:
                cycle_callback({
                    'cycle': cycle,
                    'phase': 'rotation',
                    'position_idx': position_idx,
                    'rotation': rotation,
                    'assignment': copy.deepcopy(temp_assignment),
                    'performance_comparison': performance_comparison,
                    'factory_workers': [w.to_dict() for w in factory_workers]
                })
            
            cycle += 1
        
        if position_idx < max_workers_per_station - 1:
            current_assignment, opt_details = optimize_position(
                factory_workers, current_assignment, position_idx
            )
            
            if cycle_callback:
                cycle_callback({
                    'cycle': f"Opt_{position_idx + 1}",
                    'phase': 'optimization',
                    'position_idx': position_idx,
                    'assignment': copy.deepcopy(current_assignment),
                    'optimization_details': opt_details,
                    'factory_workers': [w.to_dict() for w in factory_workers]
                })
    
    incomplete_workers = [w.worker_id for w in factory_workers if w.get_data_completeness() < 100]
    
    if incomplete_workers:
        current_assignment = collect_incomplete_worker_data_ui(
            true_workers, factory_workers, tasks, current_assignment, cycle_callback
        )
    
    return current_assignment


def collect_incomplete_worker_data_ui(
    true_workers: List[TrueWorkerProfile],
    factory_workers: List[FactoryWorkerProfile],
    tasks: List[TaskProfile],
    current_assignment: Dict[int, List[str]],
    cycle_callback: Optional[Callable] = None
) -> Dict[int, List[str]]:
    
    workers_to_process = [w.worker_id for w in factory_workers if w.get_data_completeness() < 100]
    
    if not workers_to_process:
        return current_assignment
    
    base_performance = simulate_station_performance(true_workers, tasks, current_assignment)
    factory_worker_dict = {w.worker_id: w for w in factory_workers}
    true_worker_dict = {w.worker_id: w for w in true_workers}
    
    for worker_id in workers_to_process:
        worker = factory_worker_dict[worker_id]
        missing_stations = [s for s in range(1, WSTATION + 1) if not worker.has_data_for_station(s)]
        
        current_station = None
        current_position = None
        for station_id, worker_ids in current_assignment.items():
            if worker_id in worker_ids:
                current_station = station_id
                current_position = worker_ids.index(worker_id)
                break
        
        for test_station in missing_stations:
            temp_assignment = copy.deepcopy(current_assignment)
            
            if current_station and worker_id in temp_assignment[current_station]:
                temp_assignment[current_station].remove(worker_id)
            
            if current_position is not None and current_position < len(temp_assignment[test_station]):
                temp_assignment[test_station].insert(current_position, worker_id)
            else:
                temp_assignment[test_station].append(worker_id)
            
            true_worker = true_worker_dict[worker_id]
            task = tasks[test_station - 1]
            
            individual_performance = true_worker.calculate_performance(
                test_station,
                task.delivery_time,
                task.fatigue_cost
            )
            
            base_perf = base_performance[test_station]
            if base_perf > 0:
                percentage = (individual_performance / base_perf) * 100 + 100
            else:
                percentage = 100.0
            
            factory_worker_dict[worker_id].record_performance_percentage(test_station, percentage)
            
            if cycle_callback:
                cycle_callback({
                    'cycle': f'Fix_{worker_id}_S{test_station}',
                    'phase': 'incomplete_fix',
                    'worker_id': worker_id,
                    'test_station': test_station,
                    'assignment': copy.deepcopy(temp_assignment),
                    'performance_comparison': {
                        test_station: {
                            'worker': worker_id,
                            'adjusted_percentage': percentage
                        }
                    },
                    'factory_workers': [w.to_dict() for w in factory_workers]
                })
    
    return current_assignment


# ============================================================================
# PHASE 4: OPTIMAL ASSIGNMENT CALCULATION
# ============================================================================

def find_optimal_assignment(
    factory_workers: List[FactoryWorkerProfile],
    num_workers: int,
    assignment: Dict[int, List[str]]
) -> tuple[Dict[int, List[str]], Dict]:
    
    worker_station_scores = {}
    for worker in factory_workers:
        worker_station_scores[worker.worker_id] = {}
        for station in range(1, WSTATION + 1):
            avg_pct = worker.get_average_percentage(station)
            worker_station_scores[worker.worker_id][station] = avg_pct
    
    base_workers = num_workers // WSTATION
    extra_workers = num_workers % WSTATION
    
    workers_needed_per_station = {}
    for station in range(1, WSTATION + 1):
        workers_needed_per_station[station] = base_workers + (1 if station <= extra_workers else 0)
    
    max_workers_any_station = max(workers_needed_per_station.values())
    
    optimal_assignment = {station: [] for station in range(1, WSTATION + 1)}
    assigned_workers = set()
    
    for position_idx in range(max_workers_any_station):
        station_totals = {}
        for station in range(1, WSTATION + 1):
            total = sum(worker_station_scores[wid][station] for wid in optimal_assignment[station])
            station_totals[station] = total
        
        stations_needing_worker = [s for s in range(1, WSTATION + 1) 
                                   if len(optimal_assignment[s]) < workers_needed_per_station[s]]
        
        stations_needing_worker.sort(key=lambda s: station_totals[s])
        
        for station in stations_needing_worker:
            available = [(wid, worker_station_scores[wid][station]) 
                         for wid in worker_station_scores.keys() 
                         if wid not in assigned_workers]
            
            if available:
                available.sort(key=lambda x: x[1], reverse=True)
                best_worker_id, best_score = available[0]
                
                optimal_assignment[station].append(best_worker_id)
                assigned_workers.add(best_worker_id)
    
    total_expected_performance = 0
    total_workers = 0
    station_details = {}
    for station_id, worker_ids in optimal_assignment.items():
        station_total = sum(worker_station_scores[wid][station_id] for wid in worker_ids)
        total_expected_performance += station_total
        total_workers += len(worker_ids)
        station_details[station_id] = {
            'workers': worker_ids,
            'total_performance': station_total,
            'worker_count': len(worker_ids)
        }
    
    avg_performance = total_expected_performance / total_workers if total_workers > 0 else 0
    
    # Calculate worker efficiencies in their assigned stations
    worker_efficiencies = []
    for station_id, worker_ids in optimal_assignment.items():
        for worker_id in worker_ids:
            efficiency = worker_station_scores[worker_id][station_id]
            worker_efficiencies.append({
                'worker_id': worker_id,
                'station': station_id,
                'efficiency': efficiency
            })
    
    # Sort for leaderboards
    worker_efficiencies.sort(key=lambda x: x['efficiency'], reverse=True)
    best_workers = worker_efficiencies[:3]
    worst_workers = worker_efficiencies[-3:]
    
    results = {
        'assignment': optimal_assignment,
        'worker_station_scores': worker_station_scores,
        'total_performance': total_expected_performance,
        'average_performance': avg_performance,
        'station_details': station_details,
        'best_workers': best_workers,
        'worst_workers': worst_workers
    }
    
    return optimal_assignment, results