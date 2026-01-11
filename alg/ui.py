import pygame
import sys
import os
from Algorithm import (
    TrueWorkerProfile, FactoryWorkerProfile, TaskProfile,
    generate_true_worker, generate_task_profiles,
    create_initial_assignment_sequential, simulate_station_performance,
    systematic_data_collection_ui, find_optimal_assignment,
    fire_worker_from_assignment,
    WSTATION
)

pygame.init()

SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
BLUE = (100, 150, 255)
GREEN = (100, 255, 100)
RED = (255, 100, 100)
YELLOW = (255, 255, 100)
LIGHT_BLUE = (200, 220, 255)

pygame.font.init()
FONT_SMALL = pygame.font.Font(None, 18)
FONT_MEDIUM = pygame.font.Font(None, 24)
FONT_LARGE = pygame.font.Font(None, 32)
FONT_TITLE = pygame.font.Font(None, 42)


class FactorySchedulerUI:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Factory Worker Scheduler")
        self.clock = pygame.time.Clock()
        
        if os.path.exists("Jerod.jpg"):
            self.jerod_img = pygame.image.load("Jerod.jpg")
            self.jerod_img = pygame.transform.scale(self.jerod_img, (67, 85))
        else:
            self.jerod_img = pygame.Surface((67, 85))
            self.jerod_img.fill(BLUE)
            font = pygame.font.Font(None, 16)
            text = font.render("Jerod", True, WHITE)
            self.jerod_img.blit(text, (10, 35))
        
        self.state = "hiring"
        self.true_workers = []
        self.factory_workers = []
        self.tasks = []
        self.assignment = {i: [] for i in range(1, WSTATION + 1)}
        self.current_cycle_data = None
        self.cycle_history = []
        self.current_cycle_index = 0
        self.final_results = None
        
        self.hire_button = pygame.Rect(50, 50, 200, 50)
        self.start_button = pygame.Rect(50, 120, 200, 50)
        self.next_cycle_button = pygame.Rect(50, 50, 200, 50)
        
        self.hovered_worker = None
        self.hovered_worker_rect = None
        
        self.animating = False
        self.animation_progress = 0
        self.animation_speed = 0.05
        self.old_assignment = None
        
        self.scroll_offset = 0
        self.max_scroll = 0
        
        self.tasks = generate_task_profiles()
    
    def hire_worker(self):
        # generate_true_worker() now uses the global counter automatically
        true_worker = generate_true_worker()
        factory_worker = FactoryWorkerProfile(worker_id=true_worker.worker_id)
        
        self.true_workers.append(true_worker)
        self.factory_workers.append(factory_worker)
        
        # Calculate station based on current worker count (for sequential distribution)
        worker_count = len(self.true_workers)
        station = ((worker_count - 1) % WSTATION) + 1
        self.assignment[station].append(true_worker.worker_id)
    
    def fire_worker(self, worker_id: str):
        print(f"Fire worker called for {worker_id}")
        print(f"Before: {len(self.true_workers)} true workers, {len(self.factory_workers)} factory workers")
        print(f"Before assignment: {self.assignment}")
        
        # Remove from worker lists
        self.true_workers = [w for w in self.true_workers if w.worker_id != worker_id]
        self.factory_workers = [w for w in self.factory_workers if w.worker_id != worker_id]
        
        # Rebalance assignment
        self.assignment = fire_worker_from_assignment(worker_id, self.assignment)
        
        print(f"After: {len(self.true_workers)} true workers, {len(self.factory_workers)} factory workers")
        print(f"After assignment: {self.assignment}")
        
        # Reset optimization state
        if self.state == "completed":
            self.final_results = None
            self.cycle_history = []
            self.current_cycle_index = 0
            self.current_cycle_data = None
            # Stay in completed state but with cleared results
        
        # Force screen refresh
        self.hovered_worker = None
    
    def start_optimization(self):
        if len(self.true_workers) == 0:
            return
        
        self.state = "running"
        self.cycle_history = []
        self.current_cycle_index = 0
        
        def cycle_callback(cycle_data):
            self.cycle_history.append(cycle_data)
        
        final_assignment = systematic_data_collection_ui(
            self.true_workers,
            self.factory_workers,
            self.tasks,
            self.assignment,
            cycle_callback
        )
        
        optimal_assignment, results = find_optimal_assignment(
            self.factory_workers,
            len(self.true_workers),
            self.assignment
        )
        
        self.final_results = results
        
        if self.cycle_history:
            self.current_cycle_data = self.cycle_history[0]
    
    def next_cycle(self):
        if self.current_cycle_index < len(self.cycle_history) - 1:
            self.old_assignment = self.current_cycle_data['assignment'].copy()
            self.current_cycle_index += 1
            self.current_cycle_data = self.cycle_history[self.current_cycle_index]
            self.animating = True
            self.animation_progress = 0
        else:
            self.state = "completed"
            self.assignment = self.final_results['assignment']
    
    def update_animation(self):
        if self.animating:
            self.animation_progress += self.animation_speed
            if self.animation_progress >= 1.0:
                self.animating = False
                self.animation_progress = 0
                self.old_assignment = None
    
    def draw_hiring_screen(self):
        self.screen.fill(WHITE)
        
        title = FONT_TITLE.render("Hire Employees", True, BLACK)
        self.screen.blit(title, (50, 10))
        
        pygame.draw.rect(self.screen, GREEN, self.hire_button)
        hire_text = FONT_MEDIUM.render("Hire Employee", True, BLACK)
        self.screen.blit(hire_text, (self.hire_button.x + 30, self.hire_button.y + 15))
        
        if len(self.true_workers) > 0:
            pygame.draw.rect(self.screen, BLUE, self.start_button)
            start_text = FONT_MEDIUM.render("Start", True, WHITE)
            self.screen.blit(start_text, (self.start_button.x + 70, self.start_button.y + 15))
        
        y_offset = 200 + self.scroll_offset
        
        for station in range(1, WSTATION + 1):
            station_y = y_offset + (station - 1) * 100
            
            if station_y < 180 or station_y > SCREEN_HEIGHT:
                continue
            
            station_text = FONT_MEDIUM.render(f"Station {station}", True, BLACK)
            self.screen.blit(station_text, (50, station_y))
            
            workers = self.assignment[station]
            for idx, worker_id in enumerate(workers):
                worker_x = 200 + idx * 80
                worker_y = station_y - 10
                
                self.screen.blit(self.jerod_img, (worker_x, worker_y))
                
                id_text = FONT_SMALL.render(worker_id, True, BLACK)
                self.screen.blit(id_text, (worker_x + 10, worker_y + 90))
                
                mouse_pos = pygame.mouse.get_pos()
                worker_rect = pygame.Rect(worker_x, worker_y, 67, 85)
                if worker_rect.collidepoint(mouse_pos):
                    self.hovered_worker = worker_id
                    self.hovered_worker_rect = worker_rect
    
    def draw_running_screen(self):
        self.screen.fill(WHITE)
        
        if not self.current_cycle_data:
            return
        
        cycle_num = self.current_cycle_data.get('cycle', '?')
        phase = self.current_cycle_data.get('phase', '')
        title = FONT_TITLE.render(f"Cycle {cycle_num} ({phase})", True, BLACK)
        self.screen.blit(title, (50, 10))
        
        pygame.draw.rect(self.screen, BLUE, self.next_cycle_button)
        next_text = FONT_MEDIUM.render("Next Cycle", True, WHITE)
        self.screen.blit(next_text, (self.next_cycle_button.x + 40, self.next_cycle_button.y + 15))
        
        progress_text = FONT_SMALL.render(
            f"Cycle {self.current_cycle_index + 1} / {len(self.cycle_history)}", 
            True, BLACK
        )
        self.screen.blit(progress_text, (270, 65))
        
        current_assignment = self.current_cycle_data.get('assignment', {})
        
        for station in range(1, WSTATION + 1):
            station_y = 120 + (station - 1) * 100
            
            station_text = FONT_MEDIUM.render(f"Station {station}", True, BLACK)
            self.screen.blit(station_text, (50, station_y + 30))
            
            workers = current_assignment.get(station, [])
            for idx, worker_id in enumerate(workers):
                worker_x = 200 + idx * 80
                worker_y = station_y
                
                if self.animating and self.old_assignment:
                    alpha = int(255 * self.animation_progress)
                    temp_surface = self.jerod_img.copy()
                    temp_surface.set_alpha(alpha)
                    self.screen.blit(temp_surface, (worker_x, worker_y))
                else:
                    self.screen.blit(self.jerod_img, (worker_x, worker_y))
                
                id_text = FONT_SMALL.render(worker_id, True, BLACK)
                self.screen.blit(id_text, (worker_x + 10, worker_y + 90))
                
                mouse_pos = pygame.mouse.get_pos()
                worker_rect = pygame.Rect(worker_x, worker_y, 67, 85)
                if worker_rect.collidepoint(mouse_pos):
                    self.hovered_worker = worker_id
                    self.hovered_worker_rect = worker_rect
        
        self.draw_performance_table(950, 120)
    
    def draw_performance_table(self, x: int, y: int):
        if not self.current_cycle_data:
            return
        
        phase = self.current_cycle_data.get('phase', '')
        
        # Draw appropriate table based on phase
        if phase == 'optimization':
            self.draw_optimization_table(x, y)
        elif phase == 'incomplete_fix':
            self.draw_incomplete_fix_table(x, y)
        elif phase == 'skip':
            message = self.current_cycle_data.get('message', 'Skipped')
            skip_text = FONT_MEDIUM.render(message, True, BLUE)
            self.screen.blit(skip_text, (x, y))
        else:
            # Regular performance table
            perf_comp = self.current_cycle_data.get('performance_comparison', {})
            
            if not perf_comp:
                return
            
            title = FONT_MEDIUM.render("Performance vs Base", True, BLACK)
            self.screen.blit(title, (x, y))
            
            y_offset = y + 40
            header = FONT_SMALL.render("Station | Worker | Raw % | Adjusted %", True, BLACK)
            self.screen.blit(header, (x, y_offset))
            
            pygame.draw.line(self.screen, GRAY, (x, y_offset + 25), (x + 400, y_offset + 25), 2)
            
            y_offset += 35
            for station_id, data in sorted(perf_comp.items()):
                worker = data.get('worker', '?')
                raw = data.get('raw_percentage', 0)
                adjusted = data.get('adjusted_percentage', 0)
                
                color = GREEN if adjusted > 100 else (RED if adjusted < 100 else BLACK)
                
                row_text = f"   {station_id}      {worker}    {raw-100:+.1f}%    {adjusted-100:+.1f}%"
                row = FONT_SMALL.render(row_text, True, color)
                self.screen.blit(row, (x, y_offset))
                
                y_offset += 25
    
    def draw_optimization_table(self, x: int, y: int):
        opt_details = self.current_cycle_data.get('optimization_details', {})
        
        if not opt_details:
            return
        
        title = FONT_MEDIUM.render("Position Optimization", True, BLACK)
        self.screen.blit(title, (x, y))
        
        y_offset = y + 40
        header = FONT_SMALL.render("Station | Old → New | Score", True, BLACK)
        self.screen.blit(header, (x, y_offset))
        
        pygame.draw.line(self.screen, GRAY, (x, y_offset + 25), (x + 400, y_offset + 25), 2)
        
        y_offset += 35
        for station_id, data in sorted(opt_details.items()):
            old = data.get('old_worker', '?')
            new = data.get('new_worker', '?')
            score = data.get('score', 0)
            
            row_text = f"   {station_id}     {old} → {new}   {score:.1f}%"
            row = FONT_SMALL.render(row_text, True, BLUE)
            self.screen.blit(row, (x, y_offset))
            
            y_offset += 25
    
    def draw_incomplete_fix_table(self, x: int, y: int):
        worker_id = self.current_cycle_data.get('worker_id', '?')
        test_station = self.current_cycle_data.get('test_station', '?')
        perf_comp = self.current_cycle_data.get('performance_comparison', {})
        
        title = FONT_MEDIUM.render(f"Fixing Worker {worker_id}", True, RED)
        self.screen.blit(title, (x, y))
        
        y_offset = y + 40
        info = FONT_SMALL.render(f"Testing at Station {test_station}", True, BLACK)
        self.screen.blit(info, (x, y_offset))
        
        y_offset += 30
        if test_station in perf_comp:
            percentage = perf_comp[test_station].get('adjusted_percentage', 0)
            perf_text = FONT_SMALL.render(f"Performance: {percentage:.2f}%", True, GREEN if percentage > 100 else RED)
            self.screen.blit(perf_text, (x, y_offset))
    
    def draw_completed_results(self, y_start: int):
        if not self.final_results:
            return
        
        y_offset = y_start
        x_left = 50
        x_right = 800
        
        # Title
        title = FONT_LARGE.render("Optimization Results", True, GREEN)
        self.screen.blit(title, (x_left, y_offset))
        y_offset += 50
        
        # Summary stats
        avg_perf = self.final_results.get('average_performance', 0)
        total_perf = self.final_results.get('total_performance', 0)
        
        summary1 = FONT_MEDIUM.render(f"Average Performance: {avg_perf:.2f}%", True, BLACK)
        summary2 = FONT_MEDIUM.render(f"Total Performance: {total_perf:.2f}", True, BLACK)
        
        self.screen.blit(summary1, (x_left, y_offset))
        y_offset += 30
        self.screen.blit(summary2, (x_left, y_offset))
        y_offset += 50
        
        # Worker performance matrix
        matrix_title = FONT_MEDIUM.render("Worker Performance Matrix", True, BLACK)
        self.screen.blit(matrix_title, (x_left, y_offset))
        y_offset += 35
        
        header = "Worker  "
        for s in range(1, WSTATION + 1):
            header += f"  S{s}    "
        header_text = FONT_SMALL.render(header, True, BLACK)
        self.screen.blit(header_text, (x_left, y_offset))
        y_offset += 25
        
        worker_scores = self.final_results.get('worker_station_scores', {})
        for worker in self.factory_workers:
            row = f"{worker.worker_id}   "
            for station in range(1, WSTATION + 1):
                score = worker_scores.get(worker.worker_id, {}).get(station, 0)
                row += f"{score:>6.1f}% "
            
            row_text = FONT_SMALL.render(row, True, BLACK)
            self.screen.blit(row_text, (x_left, y_offset))
            y_offset += 22
        
        y_offset += 30
        
        # Optimal assignment
        opt_title = FONT_MEDIUM.render("Optimal Assignment", True, BLACK)
        self.screen.blit(opt_title, (x_right, y_start + 50))
        
        opt_y = y_start + 85
        station_details = self.final_results.get('station_details', {})
        for station_id, details in sorted(station_details.items()):
            workers = details.get('workers', [])
            total = details.get('total_performance', 0)
            
            station_text = FONT_SMALL.render(
                f"Station {station_id}: {', '.join(workers)}", 
                True, BLACK
            )
            self.screen.blit(station_text, (x_right, opt_y))
            opt_y += 20
            
            perf_text = FONT_SMALL.render(f"  Total: {total:.1f}%", True, DARK_GRAY)
            self.screen.blit(perf_text, (x_right, opt_y))
            opt_y += 25
        
        # Leaderboards
        leader_y = y_start + 450
        self.draw_leaderboards(x_right, leader_y)
        
        self.max_scroll = max(0, y_offset - 800)
    
    def draw_leaderboards(self, x: int, y: int):
        best_workers = self.final_results.get('best_workers', [])
        worst_workers = self.final_results.get('worst_workers', [])
        
        # Best workers
        best_title = FONT_MEDIUM.render("Best Workers", True, GREEN)
        self.screen.blit(best_title, (x, y))
        y_offset = y + 35
        
        for idx, worker_data in enumerate(best_workers, 1):
            worker_id = worker_data.get('worker_id', '?')
            station = worker_data.get('station', '?')
            efficiency = worker_data.get('efficiency', 0)
            
            text = f"{idx}. {worker_id} @ S{station}: {efficiency:.1f}%"
            row = FONT_SMALL.render(text, True, BLACK)
            self.screen.blit(row, (x, y_offset))
            y_offset += 25
        
        y_offset += 20
        
        # Worst workers
        worst_title = FONT_MEDIUM.render("Workers to Fire", True, RED)
        self.screen.blit(worst_title, (x, y_offset))
        y_offset += 35
        
        for idx, worker_data in enumerate(worst_workers, 1):
            worker_id = worker_data.get('worker_id', '?')
            station = worker_data.get('station', '?')
            efficiency = worker_data.get('efficiency', 0)
            
            text = f"{idx}. {worker_id} @ S{station}: {efficiency:.1f}%"
            row = FONT_SMALL.render(text, True, BLACK)
            self.screen.blit(row, (x, y_offset))
            y_offset += 25
    
    def draw_hover_tooltip(self):
        if not self.hovered_worker:
            return
        
        true_worker = next((w for w in self.true_workers if w.worker_id == self.hovered_worker), None)
        factory_worker = next((w for w in self.factory_workers if w.worker_id == self.hovered_worker), None)
        
        if not true_worker:
            return
        
        tooltip_width = 350
        tooltip_height = 300
        tooltip = pygame.Surface((tooltip_width, tooltip_height))
        tooltip.fill(YELLOW)
        pygame.draw.rect(tooltip, BLACK, tooltip.get_rect(), 2)
        
        y_offset = 10
        name_text = FONT_MEDIUM.render("Name: Jerod", True, BLACK)
        tooltip.blit(name_text, (10, y_offset))
        
        y_offset += 30
        id_text = FONT_SMALL.render(f"Worker ID: {self.hovered_worker}", True, BLACK)
        tooltip.blit(id_text, (10, y_offset))
        
        y_offset += 25
        skills_title = FONT_SMALL.render("True Skills:", True, BLACK)
        tooltip.blit(skills_title, (10, y_offset))
        
        y_offset += 20
        for i in range(1, WSTATION + 1):
            skill = true_worker.get_skill(i)
            skill_text = FONT_SMALL.render(f"  Station {i}: {skill:.1f}", True, BLACK)
            tooltip.blit(skill_text, (10, y_offset))
            y_offset += 18
        
        # Factory worker data
        if factory_worker and self.state in ["running", "completed"]:
            y_offset += 10
            factory_title = FONT_SMALL.render("Learned Performance:", True, BLUE)
            tooltip.blit(factory_title, (10, y_offset))
            y_offset += 20
            
            for station in range(1, WSTATION + 1):
                avg = factory_worker.get_average_percentage(station)
                if avg > 0:
                    perf_text = FONT_SMALL.render(f"  Station {station}: {avg:.1f}%", True, BLACK)
                    tooltip.blit(perf_text, (10, y_offset))
                    y_offset += 18
            
            y_offset += 5
            completeness = factory_worker.get_data_completeness()
            comp_text = FONT_SMALL.render(f"Data Completeness: {completeness:.0f}%", True, GREEN if completeness == 100 else RED)
            tooltip.blit(comp_text, (10, y_offset))
        
        mouse_pos = pygame.mouse.get_pos()
        tooltip_x = min(mouse_pos[0] + 20, SCREEN_WIDTH - tooltip_width - 10)
        tooltip_y = min(mouse_pos[1] + 20, SCREEN_HEIGHT - tooltip_height - 10)
        
        self.screen.blit(tooltip, (tooltip_x, tooltip_y))

    def get_worker_at_mouse(self, mouse_pos):
        """Detect worker directly under mouse in any state"""
    
        if self.state == "completed":
            for station in range(1, WSTATION + 1):
                station_y = 200 + (station - 1) * 100
                for idx, worker_id in enumerate(self.assignment[station]):
                    worker_x = 200 + idx * 80
                    worker_y = station_y - 10
                    screen_y = worker_y - self.scroll_offset
                    if pygame.Rect(worker_x, screen_y, 67, 85).collidepoint(mouse_pos):
                        return worker_id

        elif self.state == "hiring":
            for station in range(1, WSTATION + 1):
                station_y = 200 + self.scroll_offset + (station - 1) * 100 - 10
                for idx, worker_id in enumerate(self.assignment[station]):
                    worker_x = 200 + idx * 80
                    if pygame.Rect(worker_x, station_y, 67, 85).collidepoint(mouse_pos):
                        return worker_id

        else:  # running
            for station in range(1, WSTATION + 1):
                station_y = 120 + (station - 1) * 100
                for idx, worker_id in enumerate(self.assignment.get(station, [])):
                    worker_x = 200 + idx * 80
                    if pygame.Rect(worker_x, station_y, 67, 85).collidepoint(mouse_pos):
                        return worker_id

        return None


    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                
                if event.button == 1:  # Left click
                    if self.state in ["hiring", "completed"]:
                        # Adjust button positions for scrolling
                        adjusted_hire_button = pygame.Rect(
                            self.hire_button.x, 
                            self.hire_button.y - self.scroll_offset,
                            self.hire_button.width,
                            self.hire_button.height
                        )
                        adjusted_start_button = pygame.Rect(
                            self.start_button.x,
                            self.start_button.y - self.scroll_offset,
                            self.start_button.width,
                            self.start_button.height
                        )
                        
                        if adjusted_hire_button.collidepoint(mouse_pos):
                            self.hire_worker()
                            print(f"Hired worker. Total: {len(self.true_workers)}")
                        elif adjusted_start_button.collidepoint(mouse_pos) and len(self.true_workers) > 0:
                            self.start_optimization()
                            print("Starting optimization")
                    
                    elif self.state == "running":
                        if self.next_cycle_button.collidepoint(mouse_pos):
                            self.next_cycle()
                
                elif event.button == 3:  # Right click
                    worker_id = self.get_worker_at_mouse(mouse_pos)
                    if worker_id:
                        self.fire_worker(worker_id)

            
            if event.type == pygame.MOUSEWHEEL:
                if self.state in ["hiring", "completed"]:
                    old_scroll = self.scroll_offset
                    self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset - event.y * 30))
        
        return True
    
    def run(self):
        running = True
        
        while running:
            self.clock.tick(FPS)
            self.hovered_worker = None
            self.hovered_worker_rect = None
            
            running = self.handle_events()
            
            if self.animating:
                self.update_animation()
            
            if self.state == "hiring":
                self.draw_hiring_screen()
                self.max_scroll = max(0, (WSTATION * 100 + 200) - SCREEN_HEIGHT)
            elif self.state == "running":
                self.draw_running_screen()
            elif self.state == "completed":
                # Create scrollable surface
                self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
                
                # Draw entire content on a virtual surface
                virtual_height = 200 + WSTATION * 100 + 1500  # Stations + Results
                virtual_surface = pygame.Surface((SCREEN_WIDTH, virtual_height))
                virtual_surface.fill(WHITE)
                
                # Draw title
                title = FONT_TITLE.render("Hire Employees", True, BLACK)
                virtual_surface.blit(title, (50, 10))
                
                # Draw buttons
                hire_btn_surface = pygame.Surface((200, 50))
                hire_btn_surface.fill(GREEN)
                hire_text = FONT_MEDIUM.render("Hire Employee", True, BLACK)
                hire_btn_surface.blit(hire_text, (30, 15))
                virtual_surface.blit(hire_btn_surface, (50, 50))
                
                if len(self.true_workers) > 0:
                    start_btn_surface = pygame.Surface((200, 50))
                    start_btn_surface.fill(BLUE)
                    start_text = FONT_MEDIUM.render("Start", True, WHITE)
                    start_btn_surface.blit(start_text, (70, 15))
                    virtual_surface.blit(start_btn_surface, (50, 120))
                
                # Draw stations
                for station in range(1, WSTATION + 1):
                    station_y = 200 + (station - 1) * 100
                    
                    station_text = FONT_MEDIUM.render(f"Station {station}", True, BLACK)
                    virtual_surface.blit(station_text, (50, station_y))
                    
                    workers = self.assignment[station]
                    for idx, worker_id in enumerate(workers):
                        worker_x = 200 + idx * 80
                        worker_y = station_y - 10
                        
                        virtual_surface.blit(self.jerod_img, (worker_x, worker_y))
                        
                        id_text = FONT_SMALL.render(worker_id, True, BLACK)
                        virtual_surface.blit(id_text, (worker_x + 10, worker_y + 90))
                        
                        # Check hover - adjusted for scroll
                        mouse_pos = pygame.mouse.get_pos()
                        # Calculate where this worker appears on the actual screen
                        screen_worker_x = worker_x
                        screen_worker_y = worker_y - self.scroll_offset
                        
                        # Check if mouse is over this worker on the visible screen
                        if (screen_worker_x <= mouse_pos[0] <= screen_worker_x + 67 and
                            screen_worker_y <= mouse_pos[1] <= screen_worker_y + 85 and
                            0 <= screen_worker_y <= SCREEN_HEIGHT):
                            self.hovered_worker = worker_id
                            self.hovered_worker_rect = pygame.Rect(screen_worker_x, screen_worker_y, 67, 85)
                
                # Draw results section (only if we have results)
                if self.final_results:
                    results_y = 200 + WSTATION * 100 + 50
                    
                    # Draw separator line
                    pygame.draw.line(virtual_surface, DARK_GRAY, (0, results_y - 20), (SCREEN_WIDTH, results_y - 20), 3)
                
                    y_offset = results_y
                    x_left = 50
                    x_right = 800
                    
                    # Title
                    title = FONT_LARGE.render("Optimization Results", True, GREEN)
                    virtual_surface.blit(title, (x_left, y_offset))
                    y_offset += 50
                    
                    # Summary stats
                    avg_perf = self.final_results.get('average_performance', 0)
                    total_perf = self.final_results.get('total_performance', 0)
                    
                    summary1 = FONT_MEDIUM.render(f"Average Performance: {avg_perf:.2f}%", True, BLACK)
                    summary2 = FONT_MEDIUM.render(f"Total Performance: {total_perf:.2f}", True, BLACK)
                    
                    virtual_surface.blit(summary1, (x_left, y_offset))
                    y_offset += 30
                    virtual_surface.blit(summary2, (x_left, y_offset))
                    y_offset += 50
                    
                    # Worker performance matrix
                    matrix_title = FONT_MEDIUM.render("Worker Performance Matrix", True, BLACK)
                    virtual_surface.blit(matrix_title, (x_left, y_offset))
                    y_offset += 35
                    
                    header = "Worker  "
                    for s in range(1, WSTATION + 1):
                        header += f"  S{s}    "
                    header_text = FONT_SMALL.render(header, True, BLACK)
                    virtual_surface.blit(header_text, (x_left, y_offset))
                    y_offset += 25
                    
                    worker_scores = self.final_results.get('worker_station_scores', {})
                    for worker in self.factory_workers:
                        row = f"{worker.worker_id}   "
                        for station in range(1, WSTATION + 1):
                            score = worker_scores.get(worker.worker_id, {}).get(station, 0)
                            row += f"{score:>6.1f}% "
                        
                        row_text = FONT_SMALL.render(row, True, BLACK)
                        virtual_surface.blit(row_text, (x_left, y_offset))
                        y_offset += 22
                    
                    # Optimal assignment
                    opt_title = FONT_MEDIUM.render("Optimal Assignment", True, BLACK)
                    virtual_surface.blit(opt_title, (x_right, results_y + 50))
                    
                    opt_y = results_y + 85
                    station_details = self.final_results.get('station_details', {})
                    for station_id, details in sorted(station_details.items()):
                        workers = details.get('workers', [])
                        total = details.get('total_performance', 0)
                        
                        station_text = FONT_SMALL.render(
                            f"Station {station_id}: {', '.join(workers)}", 
                            True, BLACK
                        )
                        virtual_surface.blit(station_text, (x_right, opt_y))
                        opt_y += 20
                        
                        perf_text = FONT_SMALL.render(f"  Total: {total:.1f}%", True, DARK_GRAY)
                        virtual_surface.blit(perf_text, (x_right, opt_y))
                        opt_y += 25
                    
                    # Leaderboards
                    leader_y = results_y + 450
                    
                    best_workers = self.final_results.get('best_workers', [])
                    worst_workers = self.final_results.get('worst_workers', [])
                    
                    best_title = FONT_MEDIUM.render("Best Workers", True, GREEN)
                    virtual_surface.blit(best_title, (x_right, leader_y))
                    leader_y_offset = leader_y + 35
                    
                    for idx, worker_data in enumerate(best_workers, 1):
                        worker_id = worker_data.get('worker_id', '?')
                        station = worker_data.get('station', '?')
                        efficiency = worker_data.get('efficiency', 0)
                        
                        text = f"{idx}. {worker_id} @ S{station}: {efficiency:.1f}%"
                        row = FONT_SMALL.render(text, True, BLACK)
                        virtual_surface.blit(row, (x_right, leader_y_offset))
                        leader_y_offset += 25
                    
                    leader_y_offset += 20
                    
                    worst_title = FONT_MEDIUM.render("Workers to Fire", True, RED)
                    virtual_surface.blit(worst_title, (x_right, leader_y_offset))
                    leader_y_offset += 35
                    
                    for idx, worker_data in enumerate(worst_workers, 1):
                        worker_id = worker_data.get('worker_id', '?')
                        station = worker_data.get('station', '?')
                        efficiency = worker_data.get('efficiency', 0)
                        
                        text = f"{idx}. {worker_id} @ S{station}: {efficiency:.1f}%"
                        row = FONT_SMALL.render(text, True, BLACK)
                        virtual_surface.blit(row, (x_right, leader_y_offset))
                        leader_y_offset += 25
                
                # Calculate max scroll
                self.max_scroll = max(0, virtual_height - SCREEN_HEIGHT)
                
                # Blit visible portion to screen
                visible_rect = pygame.Rect(0, self.scroll_offset, SCREEN_WIDTH, SCREEN_HEIGHT)
                self.screen.blit(virtual_surface, (0, 0), visible_rect)
            
            self.draw_hover_tooltip()
            
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    app = FactorySchedulerUI()
    app.run()