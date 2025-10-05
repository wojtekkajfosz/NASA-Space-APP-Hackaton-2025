import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import requests
from io import BytesIO
from datetime import datetime, timedelta
import random
import os
import json
import math
from fpdf import FPDF

# =========================
# GLOBALS, DATA
# =========================
script_dir = os.path.dirname(os.path.abspath(__file__))
NASA_API_KEY = os.environ.get("NASA_API_KEY", "3VJRJsAkHwn6fskCnsqVeqv3aZtfFHEx7686Gsin")

NASA_MODULES = {
    'Life Support': {'volume': 15.2, 'color': '#ff6b6b', 'icon': '🫁', 'category': 'critical', 'o2_rate': 0.84, 'co2_rate': 0.82},  # kg/day per person
    'Waste Management': {'volume': 8.1, 'color': '#8b4513', 'icon': '🚽', 'category': 'critical', 'o2_rate': 0.0, 'co2_rate': -0.5},  # CO2 scrubber
    'Thermal Control': {'volume': 12.5, 'color': '#ff8c42', 'icon': '🌡️', 'category': 'critical', 'o2_rate': 0.0, 'co2_rate': 0.0},
    'Communications': {'volume': 6.2, 'color': '#4ecdc4', 'icon': '📡', 'category': 'operations', 'o2_rate': 0.0, 'co2_rate': 0.0},
    'Power Systems': {'volume': 18.7, 'color': '#ffe66d', 'icon': '⚡', 'category': 'critical', 'o2_rate': 0.0, 'co2_rate': 0.0},
    'Stowage': {'volume': 25.8, 'color': '#a8e6cf', 'icon': '📦', 'category': 'operations', 'o2_rate': 0.0, 'co2_rate': 0.0},
    'Food Storage': {'volume': 20.4, 'color': '#ff8b94', 'icon': '🍽️', 'category': 'crew', 'o2_rate': 0.0, 'co2_rate': 0.0},
    'Medical Bay': {'volume': 16.3, 'color': '#ff9a8b', 'icon': '🏥', 'category': 'critical', 'o2_rate': 0.0, 'co2_rate': 0.0},
    'Crew Quarters': {'volume': 2.5, 'color': '#a8dadc', 'icon': '🛏️', 'category': 'crew', 'o2_rate': 0.0, 'co2_rate': 0.0},
    'Exercise Area': {'volume': 35.2, 'color': '#457b9d', 'icon': '🏃', 'category': 'crew', 'o2_rate': 0.0, 'co2_rate': 0.0},
}

placed_modules = []
habitat_config = {
    'shape': 'cylindrical',
    'length': 12.0,
    'diameter': 8.0,
    'height': 4.0,
    'crew_size': 6,
    'mission_duration': 18,  # months
    'location': 'Mars'
}

# Startup animation globals
bg_image_original = None
canvas = None
rocket_image = None
rocket_item_id = None
start_button = None
wizard_button = None

ANIMATION_STATE = {
    'running': False,
    'step': 0,
    'total_steps': 500,
    'delay_ms': 20,
    'start_x': 0,
    'end_x': 0,
    'y_pos': 0,
    'animation_id': None
}
ROCKET_SIZE = (300, 300)
Y_OFFSET_UP = 100

# =========================
# UTILS
# =========================
def calculate_habitat_volume():
    shape = habitat_config['shape']
    if shape == 'cylindrical':
        r = habitat_config['diameter'] / 2
        l = habitat_config['length']
        return math.pi * r * r * l
    elif shape == 'spherical':
        r = habitat_config['diameter'] / 2
        return (4/3) * math.pi * r * r * r
    elif shape == 'dome':
        r = habitat_config['diameter'] / 2
        h = habitat_config['height']
        return (2/3) * math.pi * r * r * r + math.pi * r * r * h
    else:
        return habitat_config['length'] * habitat_config['diameter'] * habitat_config['height']

def compute_volume(module):
    shape = module.get('shape', 'cube')
    params = module.get('params', {})
    count = module.get('count', 1)
    if shape == 'cube':
        side = params.get('side', 0)
        return (side ** 3) * count
    elif shape == 'sphere':
        r = params.get('radius', 0)
        return (4/3 * math.pi * r ** 3) * count
    elif shape == 'cylinder':
        r = params.get('radius', 0)
        h = params.get('height', 0)
        return (math.pi * r ** 2 * h) * count
    elif shape == 'hexagonal':
        side = params.get('side', 0)
        h = params.get('height', 0)
        return ((3 * math.sqrt(3) / 2) * side ** 2 * h) * count
    elif shape == 'triangle':
        side = params.get('side', 0)
        h = params.get('height', 0)
        return ((math.sqrt(3) / 4) * side ** 2 * h) * count
    else:
        return NASA_MODULES[module['name']]['volume'] * count

def calculate_used_volume():
    return sum(compute_volume(m) for m in placed_modules)

def get_utilization_percentage():
    total = calculate_habitat_volume()
    used = calculate_used_volume()
    return (used / total * 100) if total > 0 else 0

def calculate_gas_stats():
    o2_total = 0
    co2_total = 0
    crew_size = habitat_config['crew_size']
    mission_days = habitat_config['mission_duration'] * 30
    
    # Crew consumption/production
    o2_total -= crew_size * 0.84 * mission_days  # O2 consumption per person
    co2_total += crew_size * 0.82 * mission_days  # CO2 production per person
    
    # Module contributions
    for module in placed_modules:
        mod_data = NASA_MODULES[module['name']]
        count = module.get('count', 1)
        o2_total += mod_data['o2_rate'] * count * mission_days
        co2_total += mod_data['co2_rate'] * count * mission_days
    
    return {
        'o2_total': o2_total,
        'co2_total': co2_total,
        'o2_per_day': o2_total / mission_days if mission_days > 0 else 0,
        'co2_per_day': co2_total / mission_days if mission_days > 0 else 0
    }

def validate_design():
    issues = []
    crew_size = habitat_config['crew_size']
    total_vol = calculate_habitat_volume()
    vol_per_crew = total_vol / max(1, crew_size)
    if vol_per_crew < 10:
        issues.append(f"Volume per crew: {vol_per_crew:.1f} m³ (min: 10 m³)")
    critical_systems = ['Life Support', 'Waste Management', 'Medical Bay', 'Power Systems']
    for system in critical_systems:
        if not any(m['name'] == system for m in placed_modules):
            issues.append(f"Missing critical system: {system}")
    crew_quarters = sum(m.get('count', 1) for m in placed_modules if m['name'] == 'Crew Quarters')
    if crew_quarters < crew_size:
        issues.append(f"Crew Quarters: {crew_quarters}/{crew_size} needed")
    gas_stats = calculate_gas_stats()
    if gas_stats['o2_total'] < 0:
        issues.append(f"Oxygen deficit: {abs(gas_stats['o2_total']):.1f} kg over mission duration")
    if gas_stats['co2_total'] > 0:
        issues.append(f"CO2 excess: {gas_stats['co2_total']:.1f} kg over mission duration")
    return issues

def load_gif_frames(path, size=(50, 50)):
    try:
        img = Image.open(path)
        frames = []
        try:
            while True:
                frame = img.copy().resize(size, Image.Resampling.LANCZOS)
                frames.append(ImageTk.PhotoImage(frame))
                img.seek(len(frames))
        except EOFError:
            pass
        return frames
    except Exception as e:
        print(f"Error loading GIF {path}: {e}")
        return None

def animate_gif(label, frames, delay=100, index=0):
    if frames:
        label.frames = frames
        frame = frames[index]
        label.config(image=frame)
        label.image = frame
        label.after(delay, animate_gif, label, frames, delay, (index + 1) % len(frames))

# =========================
# NASA OPEN DATA (Wizard + Pictures + Space Weather)
# =========================
def fetch_nasa_insights(destination: str):
    try:
        if destination == "Mars":
            url = f"https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/latest_photos?api_key={NASA_API_KEY}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json().get("latest_photos", [])
            if data:
                first = data[0]
                return {
                    "title": f"Curiosity Rover, Sol {first.get('sol')}",
                    "subtitle": first.get("camera", {}).get("full_name", ""),
                    "image_url": first.get("img_src"),
                    "meta": f"Photos: {len(data)} | Earth date: {first.get('earth_date')}"
                }
        url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        apod = r.json()
        return {
            "title": apod.get("title", "Astronomy Picture of the Day"),
            "subtitle": apod.get("date", ""),
            "image_url": apod.get("url"),
            "meta": apod.get("explanation", "")[:240] + "..."
        }
    except Exception as e:
        return {"title": "NASA Open Data", "subtitle": "Offline / API error", "image_url": None, "meta": str(e)}

def fetch_nasa_space_weather(days_back=7, limit=6):
    start = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    base = "https://api.nasa.gov/DONKI"
    results = []
    try:
        flr = requests.get(f"{base}/FLR?startDate={start}&api_key={NASA_API_KEY}", timeout=10)
        cme = requests.get(f"{base}/CME?startDate={start}&api_key={NASA_API_KEY}", timeout=10)
        flr.raise_for_status(); cme.raise_for_status()
        flrs = flr.json() if isinstance(flr.json(), list) else []
        cmes = cme.json() if isinstance(cme.json(), list) else []
        for f in flrs:
            cls = f.get("classType") or "N/A"
            when = f.get("beginTime", "")[:16].replace("T", " ")
            results.append(("Solar Flare", f"{when} UTC • Class {cls}"))
        for m in cmes:
            speed = (m.get("speed") or "N/A")
            when = m.get("startTime", "")[:16].replace("T", " ")
            results.append(("CME", f"{when} UTC • Speed {speed} km/s"))
    except Exception as e:
        return [("Space Weather", f"API error: {e}")]
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit] if results else [("Space Weather", "No recent events")]

# =========================
# HABITAT DESIGNER WINDOW
# =========================
def open_habitat_designer(location):
    habitat_config['location'] = location

    designer_win = tk.Toplevel()
    designer_win.title(f"NASA Habitat Designer - {location}")
    designer_win.geometry("1400x900")
    designer_win.configure(bg="#1a1a2e")

    # Create a canvas for scrolling
    canvas = tk.Canvas(designer_win, bg="#1a1a2e", highlightthickness=0)
    scrollbar = tk.Scrollbar(designer_win, orient="vertical", command=canvas.yview)
    inner_frame = tk.Frame(canvas, bg="#1a1a2e")
    
    # Configure canvas and scrollbar
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Create window in canvas for inner_frame
    canvas.create_window((0, 0), window=inner_frame, anchor="nw")
    
    # Update scroll region when inner_frame size changes
    def configure_scroll_region(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    inner_frame.bind("<Configure>", configure_scroll_region)
    
    # Enable mouse wheel scrolling
    def on_mouse_wheel(event):
        if event.num == 4:
            canvas.yview_scroll(-1, "units")  # Scroll up
        elif event.num == 5:
            canvas.yview_scroll(1, "units")   # Scroll down
    
    def on_mouse_wheel_win(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    # Bind mouse wheel events (platform-specific)
    designer_win.bind_all("<MouseWheel>", on_mouse_wheel_win)  # Windows
    designer_win.bind_all("<Button-4>", on_mouse_wheel)       # Linux
    designer_win.bind_all("<Button-5>", on_mouse_wheel)       # Linux

    # LEFT
    left_frame = tk.Frame(inner_frame, bg="#16213e", width=320)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

    tk.Label(left_frame, text="Habitat Configuration",
             bg="#16213e", fg="#4a9eff", font=("Arial", 14, "bold")).pack(pady=10)

    tk.Label(left_frame, text="Habitat Shape:", bg="#16213e", fg="white").pack()
    shape_var = tk.StringVar(value=habitat_config['shape'])
    for shape in ['cylindrical', 'spherical', 'dome', 'modular']:
        tk.Radiobutton(left_frame, text=shape.capitalize(), variable=shape_var,
                       value=shape, bg="#16213e", fg="white", selectcolor="#0074D9",
                       command=lambda: update_config('shape', shape_var.get())).pack(anchor=tk.W, padx=20)

    tk.Label(left_frame, text="\nDimensions (meters)",
             bg="#16213e", fg="#4a9eff", font=("Arial", 12, "bold")).pack()

    def create_slider(label, key, from_, to, default):
        frame = tk.Frame(left_frame, bg="#16213e")
        frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(frame, text=label, bg="#16213e", fg="white").pack(side=tk.LEFT)
        var = tk.DoubleVar(value=default)
        slider = tk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL,
                          variable=var, bg="#0074D9", fg="white",
                          command=lambda v: update_config(key, float(v)))
        slider.pack(side=tk.RIGHT)
        return var

    create_slider("Length:", "length", 3, 50, habitat_config['length'])
    create_slider("Diameter:", "diameter", 3, 30, habitat_config['diameter'])
    create_slider("Height:", "height", 2, 20, habitat_config['height'])

    tk.Label(left_frame, text="\nMission Parameters",
             bg="#16213e", fg="#4a9eff", font=("Arial", 12, "bold")).pack()

    create_slider("Crew Size:", "crew_size", 1, 20, habitat_config['crew_size'])
    create_slider("Duration (months):", "mission_duration", 1, 60, habitat_config['mission_duration'])

    stats_frame = tk.Frame(left_frame, bg="#0a0a0f", relief=tk.RAISED, bd=2)
    stats_frame.pack(fill=tk.BOTH, padx=10, pady=10)

    stats_label = tk.Label(stats_frame, text="", bg="#0a0a0f", fg="#4a9eff",
                           font=("Courier", 10), justify=tk.LEFT)
    stats_label.pack(padx=10, pady=10)

    def update_stats():
        total_vol = calculate_habitat_volume()
        used_vol = calculate_used_volume()
        util = get_utilization_percentage()
        vol_per_crew = total_vol / max(1, habitat_config['crew_size'])
        gas_stats = calculate_gas_stats()
        stats_text = f"""
HABITAT STATISTICS
==================
Total Volume:  {total_vol:.1f} m³
Used Volume:   {used_vol:.1f} m³
Utilization:   {util:.1f}%
Volume/Crew:   {vol_per_crew:.1f} m³
O2 Total:      {gas_stats['o2_total']:.1f} kg
CO2 Total:     {gas_stats['co2_total']:.1f} kg
O2/Day:        {gas_stats['o2_per_day']:.2f} kg
CO2/Day:       {gas_stats['co2_per_day']:.2f} kg
Crew:          {habitat_config['crew_size']}
Duration:      {habitat_config['mission_duration']} months
Modules:       {len(placed_modules)}
        """
        stats_label.config(text=stats_text)
        designer_win.after(600, update_stats)

    update_stats()

    # CENTER
    center_frame = tk.Frame(inner_frame, bg="#0a0a0f")
    center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    tk.Label(center_frame, text="Habitat Layout Designer",
             bg="#0a0a0f", fg="#4a9eff", font=("Arial", 16, "bold")).pack(pady=10)

    design_canvas = tk.Canvas(center_frame, bg="#1a1a2e", width=700, height=600)
    design_canvas.pack(padx=10, pady=10)

    snap_to_grid_var = tk.BooleanVar(value=False)
    tk.Checkbutton(center_frame, text="Snap to Grid", variable=snap_to_grid_var,
                   bg="#0a0a0f", fg="white", selectcolor="#0074D9").pack(pady=5)

    def draw_habitat():
        design_canvas.delete("all")
        for i in range(0, 700, 20):
            design_canvas.create_line(i, 0, i, 600, fill="#2a2a3e", dash=(2, 4))
        for i in range(0, 600, 20):
            design_canvas.create_line(0, i, 700, i, fill="#2a2a3e", dash=(2, 4))

        scale = min(500 / max(1e-6, habitat_config['length']), 400 / max(1e-6, habitat_config['diameter']))
        w = habitat_config['length'] * scale
        h = habitat_config['diameter'] * scale
        x1 = (700 - w) / 2
        y1 = (600 - h) / 2
        design_canvas.habitat_bounds = (x1, y1, x1 + w, y1 + h)

        design_canvas.create_rectangle(x1, y1, x1 + w, y1 + h,
                                       outline="#4a9eff", width=3, dash=(10, 5))
        design_canvas.create_text(350, 30,
                                  text=f"{location} Habitat: {habitat_config['shape'].capitalize()}",
                                  fill="#4a9eff", font=("Arial", 14, "bold"))

    def draw_modules():
        draw_habitat()
        for idx, module in enumerate(placed_modules):
            mod_data = NASA_MODULES[module['name']]
            vol = compute_volume(module)
            eq_side = vol ** (1/3) if vol > 0 else 1
            size = max(20, eq_side * 8)
            x, y = module['x'], module['y']
            shape = module.get('shape', 'cube')
            tag = f"module_{idx}"
            # Larger hitbox for easier interaction
            design_canvas.create_rectangle(x - size/2 - 10, y - size/2 - 10, x + size/2 + 10, y + size/2 + 10,
                                          fill="", outline="", tags=tag)
            # Draw based on shape
            if shape == 'hexagonal':
                # Calculate hexagon vertices
                vertices = []
                for i in range(6):
                    angle = math.radians(60 * i)
                    vx = x + (size/2) * math.cos(angle)
                    vy = y + (size/2) * math.sin(angle)
                    vertices.extend([vx, vy])
                design_canvas.create_polygon(vertices, fill=mod_data['color'], outline="white", width=2, tags=tag)
            elif shape == 'triangle':
                # Calculate equilateral triangle vertices
                vertices = []
                for i in range(3):
                    angle = math.radians(120 * i - 90)  # Start from top
                    vx = x + (size/2) * math.cos(angle)
                    vy = y + (size/2) * math.sin(angle)
                    vertices.extend([vx, vy])
                design_canvas.create_polygon(vertices, fill=mod_data['color'], outline="white", width=2, tags=tag)
            elif shape == 'sphere':
                # Approximate sphere as a circle
                design_canvas.create_oval(x - size/2, y - size/2, x + size/2, y + size/2,
                                         fill=mod_data['color'], outline="white", width=2, tags=tag)
            elif shape == 'cylinder':
                # Approximate cylinder as a rectangle with rounded edges (simplified as rectangle)
                design_canvas.create_rectangle(x - size/2, y - size/2, x + size/2, y + size/2,
                                              fill=mod_data['color'], outline="white", width=2, tags=tag)
            else:  # cube or default
                design_canvas.create_rectangle(x - size/2, y - size/2, x + size/2, y + size/2,
                                              fill=mod_data['color'], outline="white", width=2, tags=tag)
            design_canvas.create_text(x, y, text=f"{mod_data['icon']}\n{module['name']}",
                                      fill="white", font=("Arial", 8, "bold"), tags=tag)

    draw_habitat()

    # Dragging and editing
    current_drag = None

    def start_drag(event):
        nonlocal current_drag
        item = design_canvas.find_closest(event.x, event.y)
        if item:
            tags = design_canvas.gettags(item[0])
            if tags and tags[0].startswith("module_"):
                idx = int(tags[0].split("_")[1])
                current_drag = idx
                module = placed_modules[idx]
                module['offset_x'] = event.x - module['x']
                module['offset_y'] = event.y - module['y']
                design_canvas.itemconfig(f"module_{idx}", outline="yellow", width=3)

    def drag(event):
        nonlocal current_drag
        if current_drag is not None:
            module = placed_modules[current_drag]
            x = event.x - module.get('offset_x', 0)
            y = event.y - module.get('offset_y', 0)
            vol = compute_volume(module)
            eq_side = vol ** (1/3) if vol > 0 else 1
            size = max(20, eq_side * 8)
            x1, y1, x2, y2 = design_canvas.habitat_bounds
            x = max(x1 + size/2, min(x2 - size/2, x))
            y = max(y1 + size/2, min(y2 - size/2, y))
            if snap_to_grid_var.get():
                grid_size = 20
                x = round(x / grid_size) * grid_size
                y = round(y / grid_size) * grid_size
            module['x'] = x
            module['y'] = y
            draw_modules()

    def stop_drag(event):
        nonlocal current_drag
        if current_drag is not None:
            design_canvas.itemconfig(f"module_{current_drag}", outline="white", width=2)
            current_drag = None

    def delete_module(event):
        item = design_canvas.find_closest(event.x, event.y)
        if item:
            tags = design_canvas.gettags(item[0])
            if tags and tags[0].startswith("module_"):
                idx = int(tags[0].split("_")[1])
                if messagebox.askyesno("Delete Module", f"Delete {placed_modules[idx]['name']}?"):
                    placed_modules.pop(idx)
                    draw_modules()

    def edit_module(event):
        item = design_canvas.find_closest(event.x, event.y)
        if item:
            tags = design_canvas.gettags(item[0])
            if tags and tags[0].startswith("module_"):
                idx = int(tags[0].split("_")[1])
                module = placed_modules[idx]
                edit_win = tk.Toplevel(designer_win)
                edit_win.title(f"Edit {module['name']}")
                tk.Label(edit_win, text="Shape:").pack()
                shape_var = tk.StringVar(value=module.get('shape', 'cube'))
                shapes = ['cube', 'sphere', 'cylinder', 'hexagonal', 'triangle']
                ttk.Combobox(edit_win, values=shapes, textvariable=shape_var).pack()
                param_frame = tk.Frame(edit_win)
                param_frame.pack()
                params_vars = {}
                def update_params(*args):
                    for w in param_frame.winfo_children():
                        w.destroy()
                    sh = shape_var.get()
                    if sh == 'cube':
                        side = tk.DoubleVar(value=module['params'].get('side', 0))
                        tk.Label(param_frame, text="Side (m):").pack()
                        tk.Entry(param_frame, textvariable=side).pack()
                        params_vars['side'] = side
                    elif sh == 'sphere':
                        r = tk.DoubleVar(value=module['params'].get('radius', 0))
                        tk.Label(param_frame, text="Radius (m):").pack()
                        tk.Entry(param_frame, textvariable=r).pack()
                        params_vars['radius'] = r
                    elif sh == 'cylinder':
                        r = tk.DoubleVar(value=module['params'].get('radius', 0))
                        h = tk.DoubleVar(value=module['params'].get('height', 0))
                        tk.Label(param_frame, text="Radius (m):").pack()
                        tk.Entry(param_frame, textvariable=r).pack()
                        tk.Label(param_frame, text="Height (m):").pack()
                        tk.Entry(param_frame, textvariable=h).pack()
                        params_vars['radius'] = r
                        params_vars['height'] = h
                    elif sh in ['hexagonal', 'triangle']:
                        side = tk.DoubleVar(value=module['params'].get('side', 0))
                        h = tk.DoubleVar(value=module['params'].get('height', 0))
                        tk.Label(param_frame, text="Side (m):").pack()
                        tk.Entry(param_frame, textvariable=side).pack()
                        tk.Label(param_frame, text="Height (m):").pack()
                        tk.Entry(param_frame, textvariable=h).pack()
                        params_vars['side'] = side
                        params_vars['height'] = h
                shape_var.trace("w", update_params)
                update_params()
                def save():
                    module['shape'] = shape_var.get()
                    module['params'] = {k: v.get() for k, v in params_vars.items()}
                    draw_modules()
                    edit_win.destroy()
                tk.Button(edit_win, text="Save", command=save).pack()

    design_canvas.bind("<Button-1>", start_drag)
    design_canvas.bind("<B1-Motion>", drag)
    design_canvas.bind("<ButtonRelease-1>", stop_drag)
    design_canvas.bind("<Double-Button-1>", edit_module)
    design_canvas.bind("<Button-3>", delete_module)

    # RIGHT
    right_frame = tk.Frame(inner_frame, bg="#16213e", width=320)
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

    tk.Label(right_frame, text="Module Library",
             bg="#16213e", fg="#4a9eff", font=("Arial", 14, "bold")).pack(pady=10)

    module_frame = tk.Frame(right_frame, bg="#16213e")
    module_frame.pack(fill=tk.BOTH, padx=10, pady=5)

    def add_module(module_name):
        module_data = NASA_MODULES[module_name]
        default_vol = module_data['volume']
        default_side = default_vol ** (1/3)
        placed_modules.append({
            'name': module_name,
            'shape': 'cube',
            'params': {'side': round(default_side, 1)},
            'x': random.randint(100, 600),
            'y': random.randint(100, 500),
            'count': 1
        })
        draw_modules()

    for module_name, module_data in NASA_MODULES.items():
        btn_frame = tk.Frame(module_frame, bg="#0a0a0f", relief=tk.RAISED, bd=1)
        btn_frame.pack(fill=tk.X, pady=3)

        tk.Label(btn_frame, text=module_data['icon'], bg="#0a0a0f",
                 fg=module_data['color'], font=("Arial", 16)).pack(side=tk.LEFT, padx=5)

        info_frame = tk.Frame(btn_frame, bg="#0a0a0f")
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(info_frame, text=module_name, bg="#0a0a0f", fg="white",
                 font=("Arial", 10, "bold")).pack(anchor=tk.W)
        tk.Label(info_frame, text=f"{module_data['volume']} m³", bg="#0a0a0f",
                 fg="#888", font=("Arial", 8)).pack(anchor=tk.W)
        tk.Label(info_frame, text=f"O2: {module_data['o2_rate']} kg/day", bg="#0a0a0f",
                 fg="#888", font=("Arial", 8)).pack(anchor=tk.W)
        tk.Label(info_frame, text=f"CO2: {module_data['co2_rate']} kg/day", bg="#0a0a0f",
                 fg="#888", font=("Arial", 8)).pack(anchor=tk.W)

        tk.Button(btn_frame, text="+", bg="#0074D9", fg="white",
                  command=lambda m=module_name: add_module(m)).pack(side=tk.RIGHT, padx=5)

    def check_validation():
        issues = validate_design()
        if not issues:
            messagebox.showinfo("Design Valid",
                                "Excellent! Your habitat design meets NASA requirements!")
        else:
            messagebox.showwarning("Design Issues",
                                   "Issues found:\n\n" + "\n".join(issues))

    tk.Button(right_frame, text="Validate Design",
              bg="#00cc66", fg="white", font=("Arial", 12, "bold"),
              command=check_validation).pack(pady=10, fill=tk.X, padx=10)

    def import_design():
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Import Habitat Design"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                global habitat_config, placed_modules
                habitat_config.update(data.get('habitat', {}))
                placed_modules.clear()
                placed_modules.extend(data.get('modules', []))
                shape_var.set(habitat_config['shape'])
                draw_habitat()
                messagebox.showinfo("Imported", f"Design loaded from:\n{filename}")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to load design: {str(e)}")

    tk.Button(right_frame, text="Import Design",
              bg="#0074D9", fg="white", font=("Arial", 12),
              command=import_design).pack(pady=5, fill=tk.X, padx=10)

    def export_design_json():
        design_data = {
            'habitat': habitat_config,
            'modules': placed_modules,
            'statistics': {
                'total_volume': calculate_habitat_volume(),
                'used_volume': calculate_used_volume(),
                'utilization': get_utilization_percentage(),
                'gas_stats': calculate_gas_stats()
            }
        }
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"habitat_{location}_{datetime.now().strftime('%Y%m%d')}.json"
        )
        if filename:
            with open(filename, 'w') as f:
                json.dump(design_data, f, indent=2)
            messagebox.showinfo("Saved", f"Design saved to:\n{filename}")

    tk.Button(right_frame, text="Export JSON",
              bg="#0074D9", fg="white", font=("Arial", 12),
              command=export_design_json).pack(pady=5, fill=tk.X, padx=10)

    def export_design_pdf():
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, f"NASA Habitat Design - {location}", ln=True, align="C")
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        
        pdf.cell(0, 10, f"Habitat Configuration", ln=True)
        pdf.cell(0, 10, f"Shape: {habitat_config['shape'].capitalize()}", ln=True)
        pdf.cell(0, 10, f"Length: {habitat_config['length']:.1f} m", ln=True)
        pdf.cell(0, 10, f"Diameter: {habitat_config['diameter']:.1f} m", ln=True)
        pdf.cell(0, 10, f"Height: {habitat_config['height']:.1f} m", ln=True)
        pdf.cell(0, 10, f"Crew Size: {habitat_config['crew_size']}", ln=True)
        pdf.cell(0, 10, f"Mission Duration: {habitat_config['mission_duration']} months", ln=True)
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Statistics", ln=True)
        pdf.set_font("Arial", size=12)
        stats = calculate_gas_stats()
        pdf.cell(0, 10, f"Total Volume: {calculate_habitat_volume():.1f} m³", ln=True)
        pdf.cell(0, 10, f"Used Volume: {calculate_used_volume():.1f} m³", ln=True)
        pdf.cell(0, 10, f"Utilization: {get_utilization_percentage():.1f}%", ln=True)
        pdf.cell(0, 10, f"O2 Total: {stats['o2_total']:.1f} kg", ln=True)
        pdf.cell(0, 10, f"CO2 Total: {stats['co2_total']:.1f} kg", ln=True)
        pdf.cell(0, 10, f"O2/Day: {stats['o2_per_day']:.2f} kg", ln=True)
        pdf.cell(0, 10, f"CO2/Day: {stats['co2_per_day']:.2f} kg", ln=True)
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Modules", ln=True)
        pdf.set_font("Arial", size=12)
        for module in placed_modules:
            mod_data = NASA_MODULES[module['name']]
            pdf.cell(0, 10, f"{module['name']} (x{module.get('count', 1)}): {compute_volume(module):.1f} m³", ln=True)
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"habitat_{location}_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        if filename:
            pdf.output(filename)
            messagebox.showinfo("Saved", f"Design saved to:\n{filename}")

    tk.Button(right_frame, text="Export PDF",
              bg="#0074D9", fg="white", font=("Arial", 12),
              command=export_design_pdf).pack(pady=5, fill=tk.X, padx=10)

    def clear_all():
        if messagebox.askyesno("Clear All", "Remove all modules?"):
            placed_modules.clear()
            draw_habitat()

    tk.Button(right_frame, text="Clear All",
              bg="#cc0000", fg="white", font=("Arial", 12),
              command=clear_all).pack(pady=5, fill=tk.X, padx=10)

    def update_config(key, value):
        habitat_config[key] = value
        draw_habitat()

# =========================
# NASA PICTURES WINDOW (APOD/Mars) + Space Weather → Designer
# =========================
def open_apod_window(location):
    global root
    root.destroy()
    root = tk.Tk()
    root.title(f"{location} - NASA Space Apps Challenge")
    root.configure(bg="#222")
    root.geometry("900x900")

    img_label = tk.Label(root, bg="#222")
    img_label.place(x=0, y=0)
    text_label = tk.Label(root, text="", bg="#222", fg="#fff", font=("Arial", 18))
    text_label.place(relx=0.5, rely=0.05, anchor="center")

    def set_apod_background():
        start_date = datetime(2015, 1, 1)
        end_date = datetime.now()
        rand_date = start_date + (end_date - start_date) * random.random()
        current_date = rand_date.strftime("%Y-%m-%d")
        api_url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}&date={current_date}"
        try:
            r = requests.get(api_url, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data.get("media_type") == "image":
                img_url = data["url"]
                ir = requests.get(img_url, timeout=10)
                ir.raise_for_status()
                img = Image.open(BytesIO(ir.content))
                img.thumbnail((900, 700))
                photo = ImageTk.PhotoImage(img)
                img_label.config(image=photo)
                img_label.image = photo
                text_label.config(text=f"NASA Picture of the Day: {data.get('date', current_date)}")
            else:
                text_label.config(text=f"No image available for {current_date}")
        except requests.RequestException as e:
            text_label.config(text=f"Error fetching APOD: {str(e)}")

    def set_moon_background():
        moon_url = "https://images-assets.nasa.gov/image/PIA00405/PIA00405~large.jpg"
        try:
            ir = requests.get(moon_url, timeout=10)
            ir.raise_for_status()
            img = Image.open(BytesIO(ir.content))
            img.thumbnail((900, 700))
            photo = ImageTk.PhotoImage(img)
            img_label.config(image=photo)
            img_label.image = photo
            text_label.config(text="NASA Moon Image")
        except requests.RequestException as e:
            text_label.config(text=f"Error fetching Moon image: {str(e)}")

    def set_mars_background():
        info = fetch_nasa_insights("Mars")
        url = info.get("image_url") or "https://mars.nasa.gov/msl-raw-images/msss/01000/mcam/1000ML0044631300305227E03_DXXX.jpg"
        try:
            ir = requests.get(url, timeout=10)
            ir.raise_for_status()
            img = Image.open(BytesIO(ir.content))
            img.thumbnail((900, 700))
            photo = ImageTk.PhotoImage(img)
            img_label.config(image=photo)
            img_label.image = photo
            text_label.config(text=info.get("title", "NASA Mars Image"))
        except requests.RequestException as e:
            text_label.config(text=f"Error fetching Mars image: {str(e)}")

    def open_space_weather_window():
        win = tk.Toplevel(root)
        win.title("Space Weather (NASA DONKI)")
        win.geometry("560x360")
        win.configure(bg="#111")
        tk.Label(win, text="Recent Space Weather Events (last 7 days)", bg="#111", fg="#4a9eff",
                 font=("Arial", 14, "bold")).pack(pady=8)
        list_frame = tk.Frame(win, bg="#111"); list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        canvas_sw = tk.Canvas(list_frame, bg="#111", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas_sw.yview)
        inner = tk.Frame(canvas_sw, bg="#111")
        inner.bind("<Configure>", lambda e: canvas_sw.configure(scrollregion=canvas_sw.bbox("all")))
        canvas_sw.create_window((0, 0), window=inner, anchor="nw")
        canvas_sw.configure(yscrollcommand=scrollbar.set)
        canvas_sw.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        events = fetch_nasa_space_weather()
        for kind, text in events:
            row = tk.Frame(inner, bg="#1b1b1b"); row.pack(fill=tk.X, pady=4)
            tk.Label(row, text=kind, width=12, bg="#1b1b1b", fg="#ffd166", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=6)
            tk.Label(row, text=text, bg="#1b1b1b", fg="#ddd", font=("Arial", 11), wraplength=420, justify="left").pack(side=tk.LEFT, padx=6)

        tk.Button(win, text="Close", command=win.destroy, bg="#333", fg="#fff").pack(pady=8)

    if location == "Moon":
        set_moon_background()
    elif location == "Outer Space":
        set_apod_background()
    elif location == "Mars":
        set_mars_background()

    tk.Button(root, text="Design Habitat", command=lambda: open_habitat_designer(location),
              bg="#00cc66", fg="#fff", font=("Arial", 16, "bold"),
              relief=tk.RAISED, padx=30, pady=10).place(relx=0.5, rely=0.85, anchor="center")

    if location == "Outer Space":
        tk.Button(root, text="Generate New Image", command=set_apod_background,
                  bg="#0074D9", fg="#fff", font=("Arial", 14), relief=tk.RAISED, padx=20, pady=5).place(relx=0.5, rely=0.75, anchor="center")
    tk.Button(root, text="Space Weather", command=open_space_weather_window,
              bg="#ff8c42", fg="#fff", font=("Arial", 14), relief=tk.RAISED, padx=20, pady=5).place(relx=0.5, rely=0.80, anchor="center")

    if location == "Outer Space":
        tk.Button(root, text="Go to: Moon", command=lambda: open_apod_window("Moon"),
                  bg="#0074D9", fg="#fff", font=("Arial", 12)).place(relx=0.95, rely=0.90, anchor="se")
        tk.Button(root, text="Go to: Mars", command=lambda: open_apod_window("Mars"),
                  bg="#0074D9", fg="#fff", font=("Arial", 12)).place(relx=0.95, rely=0.95, anchor="se")
    elif location == "Moon":
        tk.Button(root, text="Go to: Outer Space", command=lambda: open_apod_window("Outer Space"),
                  bg="#0074D9", fg="#fff", font=("Arial", 12)).place(relx=0.95, rely=0.90, anchor="se")
        tk.Button(root, text="Go to: Mars", command=lambda: open_apod_window("Mars"),
                  bg="#0074D9", fg="#fff", font=("Arial", 12)).place(relx=0.95, rely=0.95, anchor="se")
    elif location == "Mars":
        tk.Button(root, text="Go to: Outer Space", command=lambda: open_apod_window("Outer Space"),
                  bg="#0074D9", fg="#fff", font=("Arial", 12)).place(relx=0.95, rely=0.90, anchor="se")
        tk.Button(root, text="Go to: Moon", command=lambda: open_apod_window("Moon"),
                  bg="#0074D9", fg="#fff", font=("Arial", 12)).place(relx=0.95, rely=0.95, anchor="se")

    root.mainloop()

# =========================
# LOCATION SELECTOR
# =========================
def open_location_selector():
    global root
    root.destroy()

    root = tk.Tk()
    root.title("POLIN Space Society - Location Selection")
    root.configure(bg="#222")
    root.geometry("600x500")

    tk.Label(root, text="POLIN SPACE SOCIETY",
             bg="#222", fg="#4a9eff", font=("Arial", 24, "bold")).pack(pady=10)
    tk.Label(root, text="NASA Space Apps Challenge 2025\nHabitat Layout Creator",
             bg="#222", fg="#fff", font=("Arial", 14)).pack(pady=5)
    tk.Label(root, text="Where do You want to build Your space habitat?",
             bg="#222", fg="#fff", font=("Arial", 16)).pack(pady=20)

    button_frame = tk.Frame(root, bg="#222")
    button_frame.pack(pady=10)

    outer_space_frames = load_gif_frames(os.path.join(script_dir, "OuterSpace.gif"), size=(100, 100))
    moon_frames = load_gif_frames(os.path.join(script_dir, "Moon.gif"), size=(100, 100))
    mars_frames = load_gif_frames(os.path.join(script_dir, "MARS.gif"), size=(100, 100))

    outer_space_label = tk.Label(button_frame, bg="#222"); outer_space_label.grid(row=0, column=0, padx=20, pady=10)
    if outer_space_frames: animate_gif(outer_space_label, outer_space_frames, delay=120)
    tk.Button(button_frame, text="Outer Space",
              command=lambda: open_apod_window("Outer Space"),
              bg="#0074D9", fg="#fff", font=("Arial", 12)).grid(row=1, column=0)

    moon_label = tk.Label(button_frame, bg="#222"); moon_label.grid(row=0, column=1, padx=20, pady=10)
    if moon_frames: animate_gif(moon_label, moon_frames, delay=120)
    tk.Button(button_frame, text="Moon",
              command=lambda: open_apod_window("Moon"),
              bg="#0074D9", fg="#fff", font=("Arial", 12)).grid(row=1, column=1)

    mars_label = tk.Label(button_frame, bg="#222"); mars_label.grid(row=0, column=2, padx=20, pady=10)
    if mars_frames: animate_gif(mars_label, mars_frames, delay=120)
    tk.Button(button_frame, text="Mars",
              command=lambda: open_apod_window("Mars"),
              bg="#0074D9", fg="#fff", font=("Arial", 12)).grid(row=1, column=2)

    tk.Label(root, text="International Team from 7 countries",
             bg="#222", fg="#4a9eff", font=("Arial", 12)).pack(pady=20)

    root.mainloop()

# =========================
# STARTUP BACKGROUND + ROCKET
# =========================
def animate_rocket():
    global ANIMATION_STATE, rocket_item_id, canvas
    if not ANIMATION_STATE['running'] or rocket_item_id is None or canvas is None:
        return
    step = ANIMATION_STATE['step']
    total_steps = ANIMATION_STATE['total_steps']
    if step <= total_steps:
        x_start = ANIMATION_STATE['start_x']
        x_end = ANIMATION_STATE['end_x']
        current_x = x_start + (x_end - x_start) * (step / total_steps)
        canvas.coords(rocket_item_id, current_x, ANIMATION_STATE['y_pos'])
        ANIMATION_STATE['step'] += 1
        if ANIMATION_STATE['step'] > total_steps:
            ANIMATION_STATE['step'] = 0
        ANIMATION_STATE['animation_id'] = root.after(ANIMATION_STATE['delay_ms'], animate_rocket)

def resize_background(event):
    global bg_image_original, canvas, rocket_image, rocket_item_id, ANIMATION_STATE, start_button, wizard_button
    if bg_image_original is None or canvas is None:
        return
    new_width, new_height = event.width, event.height
    if new_width == 0 or new_height == 0:
        return
    original_width, original_height = bg_image_original.size
    scale = max(new_width / original_width, new_height / original_height)
    scaled_width = int(original_width * scale) + 2
    scaled_height = int(original_height * scale)
    resized_image = bg_image_original.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    root.bg_image_tk = ImageTk.PhotoImage(resized_image)
    canvas.delete("all")
    x_offset = (new_width - scaled_width) // 2
    y_offset = (new_height - scaled_height) // 2
    canvas.create_image(x_offset, y_offset, anchor="nw", image=root.bg_image_tk)

    if rocket_image:
        if ANIMATION_STATE['animation_id']:
            root.after_cancel(ANIMATION_STATE['animation_id'])
            ANIMATION_STATE['running'] = False
        rocket_width = ROCKET_SIZE[0]
        start_x = -rocket_width / 2
        end_x = new_width + rocket_width / 2
        y_pos = new_height // 2 - Y_OFFSET_UP
        rocket_item_id = canvas.create_image(start_x, y_pos, image=rocket_image, anchor="center")
        ANIMATION_STATE.update({'running': True, 'step': 0, 'start_x': start_x, 'end_x': end_x, 'y_pos': y_pos})
        animate_rocket()

    if start_button:
        start_button.place(relx=0.5, rely=0.5, anchor="center")
    if wizard_button:
        wizard_button.place(relx=0.5, rely=0.65, anchor="center")

# =========================
# DESIGN WIZARD
# =========================
def open_design_wizard():
    wizard = tk.Toplevel()
    wizard.title("Design Wizard")
    wizard.geometry("1200x780")
    wizard.configure(bg="#efefef")

    current_step = tk.IntVar(value=1)
    state = {
        "design_name": tk.StringVar(value="My Space Habitat"),
        "habitat_type": tk.StringVar(value="Cylindrical"),
        "launch_system": tk.StringVar(value="Falcon Heavy"),
        "destination": tk.StringVar(value=habitat_config.get('location', 'Mars')),
        "crew_size": tk.IntVar(value=habitat_config['crew_size']),
        "mission_days": tk.IntVar(value=habitat_config['mission_duration'] * 30),
        "length": tk.DoubleVar(value=habitat_config['length']),
        "width": tk.DoubleVar(value=habitat_config['diameter']),
        "height": tk.DoubleVar(value=habitat_config['height']),
        "shape": tk.StringVar(value=habitat_config['shape']),
        "countdown": tk.IntVar(value=5),
        "testing": False
    }

    header = tk.Frame(wizard, bg="#efefef")
    header.pack(fill=tk.X, pady=10)
    title = tk.Label(header, text="FIRST STEP", font=("Arial", 32, "bold"), bg="#efefef")
    title.pack()

    content = tk.Frame(wizard, bg="#efefef")
    content.pack(fill=tk.BOTH, expand=True, padx=24, pady=10)

    nav = tk.Frame(wizard, bg="#efefef")
    nav.pack(fill=tk.X, pady=10)

    def step1():
        frame = tk.Frame(content, bg="#efefef")
        frame.pack(fill=tk.BOTH, expand=True)
        def row(r, txt, w):
            tk.Label(frame, text=txt, font=("Arial", 20, "bold"), bg="#efefef").grid(row=r, column=0, sticky="e", padx=12, pady=12)
            w.grid(row=r, column=1, sticky="we", padx=12, pady=12)
            frame.grid_columnconfigure(1, weight=1)
        row(0, "Design name:", tk.Entry(frame, textvariable=state["design_name"], font=("Arial", 18)))
        row(1, "Habitat type:", ttk.Combobox(frame, values=["Cylindrical", "Spherical", "Dome", "Modular"],
                                             textvariable=state["habitat_type"], state="readonly"))
        row(2, "Launch system:", ttk.Combobox(frame, values=["Falcon Heavy", "SLS", "Starship", "Vulcan"],
                                              textvariable=state["launch_system"], state="readonly"))
        dest_row = tk.Frame(frame, bg="#efefef"); row(3, "Destination:", dest_row)
        os_frames = load_gif_frames(os.path.join(script_dir, "OuterSpace.gif"), size=(90, 90))
        moon_frames = load_gif_frames(os.path.join(script_dir, "Moon.gif"), size=(90, 90))
        mars_frames = load_gif_frames(os.path.join(script_dir, "MARS.gif"), size=(90, 90))
        def dest(col, frames, label, val):
            h = tk.Frame(dest_row, bg="#efefef"); h.grid(row=0, column=col, padx=18)
            L = tk.Label(h, bg="#efefef"); L.pack()
            if frames: animate_gif(L, frames, delay=120)
            tk.Button(h, text=label, command=lambda: state["destination"].set(val),
                      bg="#111", fg="#fff").pack(pady=4)
        dest(0, os_frames, "OUTER SPACE", "Outer Space")
        dest(1, moon_frames, "MOON", "Moon")
        dest(2, mars_frames, "MARS", "Mars")
        row(4, "Crew size:", tk.Spinbox(frame, from_=1, to=50, textvariable=state["crew_size"], font=("Arial", 18), width=8))
        row(5, "Mission duration (days):", tk.Spinbox(frame, from_=1, to=3650, textvariable=state["mission_days"], font=("Arial", 18), width=8))

    def step2():
        frame = tk.Frame(content, bg="#efefef")
        frame.pack(fill=tk.BOTH, expand=True)
        astro_frames = load_gif_frames(os.path.join(script_dir, "astro walking FINAL.gif"), size=(100, 100))
        if astro_frames:
            left_astro_label = tk.Label(frame, bg="#efefef")
            left_astro_label.place(relx=0.0, rely=1.0, anchor="sw")
            animate_gif(left_astro_label, astro_frames, delay=120)
            right_astro_label = tk.Label(frame, bg="#efefef")
            right_astro_label.place(relx=1.0, rely=1.0, anchor="se")
            animate_gif(right_astro_label, astro_frames, delay=120)
        top = tk.Frame(frame, bg="#efefef"); top.pack(pady=6)
        ttk.Combobox(top, values=["cylindrical", "spherical", "dome", "modular"],
                     textvariable=state["shape"], state="readonly", width=22).pack()
        sliders = tk.Frame(frame, bg="#efefef"); sliders.pack(fill=tk.X, padx=10, pady=10)
        def add_slider(label, var, a, b):
            row = tk.Frame(sliders, bg="#efefef"); row.pack(fill=tk.X, pady=6)
            tk.Label(row, text=label, font=("Arial", 18, "bold"), bg="#efefef").pack(side=tk.LEFT, padx=10)
            tk.Scale(row, from_=a, to=b, orient=tk.HORIZONTAL, variable=var, resolution=0.1, length=620).pack(side=tk.LEFT, padx=10)
        add_slider("Length (m):", state["length"], 1, 120)
        add_slider("Width (m):", state["width"], 1, 120)
        add_slider("Height (m):", state["height"], 1, 60)
        body = tk.Frame(frame, bg="#efefef"); body.pack(expand=True, pady=6)
        preview = tk.Canvas(body, width=420, height=360, bg="#1a1a2e", highlightthickness=0); preview.grid(row=0, column=0, padx=18)
        side = tk.Frame(body, bg="#efefef"); side.grid(row=0, column=1, sticky="n", padx=18)
        cur_var = tk.StringVar(value=""); max_var = tk.StringVar(value="")
        tk.Label(side, text="Current volume:", font=("Arial", 16, "bold"), bg="#efefef").pack(anchor="w")
        tk.Entry(side, textvariable=cur_var, width=22).pack(pady=4)
        tk.Label(side, text="Maximum volume:", font=("Arial", 16, "bold"), bg="#efefef").pack(anchor="w", pady=(10,0))
        tk.Entry(side, textvariable=max_var, width=22).pack(pady=4)
        def redraw():
            preview.delete("all")
            for i in range(0, 420, 10): preview.create_line(i, 0, i, 360, fill="#2a2a3e")
            for i in range(0, 360, 10): preview.create_line(0, i, 420, i, fill="#2a2a3e")
            shape = state["shape"].get(); L = state["length"].get(); W = state["width"].get(); H = state["height"].get()
            prev = (habitat_config['shape'], habitat_config['length'], habitat_config['diameter'], habitat_config['height'])
            habitat_config['shape'], habitat_config['length'], habitat_config['diameter'], habitat_config['height'] = shape, L, W, H
            vol = calculate_habitat_volume()
            cur_var.set(f"{vol:.1f} m³"); max_var.set(f"{(L*W*max(1,H)):.1f} m³")
            habitat_config['shape'], habitat_config['length'], habitat_config['diameter'], habitat_config['height'] = prev
            scale = min(340/max(L, 1e-6), 240/max(W, 1e-6)); w = max(20, L*scale); h = max(20, W*scale)
            x1 = (420 - w)/2; y1 = (360 - h)/2
            preview.create_rectangle(x1, y1, x1+w, y1+h, outline="#4a9eff", width=3)
            preview.create_text(210, 20, text=f"{shape.capitalize()} {L:.1f}x{W:.1f}x{H:.1f}", fill="#4a9eff", font=("Arial", 12, "bold"))
        for v in [state["shape"], state["length"], state["width"], state["height"]]:
            v.trace_add("write", lambda *a: redraw())
        redraw()

    def step3():
        frame = tk.Frame(content, bg="#efefef"); frame.pack(fill=tk.BOTH, expand=True)
        dest = state["destination"].get()
        info = fetch_nasa_insights(dest)
        top = tk.Frame(frame, bg="#efefef"); top.pack(fill=tk.X, pady=6)
        tk.Label(top, text="SAVE • SHARE WITH YOUR FRIENDS OR TEAM", font=("Arial", 22, "bold"), bg="#efefef").pack()

        nasa = tk.Frame(frame, bg="#f6f6f6", bd=1, relief=tk.SOLID); nasa.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(nasa, text="NASA Open Data", font=("Arial", 16, "bold"), bg="#f6f6f6").pack(anchor="w", padx=10, pady=(8,0))
        tk.Label(nasa, text=f"Destination: {dest}", font=("Arial", 12), bg="#f6f6f6").pack(anchor="w", padx=10)
        img_label = tk.Label(nasa, bg="#f6f6f6"); img_label.pack(side=tk.LEFT, padx=10, pady=10)
        if info.get("image_url"):
            try:
                r = requests.get(info["image_url"], timeout=10); r.raise_for_status()
                pil = Image.open(BytesIO(r.content)).resize((260, 160), Image.Resampling.LANCZOS)
                img_label.photo = ImageTk.PhotoImage(pil); img_label.config(image=img_label.photo)
            except Exception:
                pass
        text_box = tk.Frame(nasa, bg="#f6f6f6"); text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(text_box, text=info.get("title",""), font=("Arial", 14, "bold"), bg="#f6f6f6").pack(anchor="w")
        tk.Label(text_box, text=info.get("subtitle",""), font=("Arial", 11), bg="#f6f6f6", fg="#666").pack(anchor="w")
        tk.Label(text_box, text=info.get("meta",""), font=("Arial", 11), bg="#f6f6f6", wraplength=700, justify="left").pack(anchor="w", pady=(6,0))

        sw = tk.Frame(frame, bg="#f6fff6", bd=1, relief=tk.SOLID); sw.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(sw, text="Space Weather (NASA DONKI – last 7 days)", font=("Arial", 14, "bold"), bg="#f6fff6", fg="#0a7f2e").pack(anchor="w", padx=10, pady=(8,4))
        events = fetch_nasa_space_weather()
        if events:
            for kind, text in events:
                row = tk.Frame(sw, bg="#f6fff6"); row.pack(fill=tk.X, padx=10, pady=2)
                tk.Label(row, text=kind, width=12, anchor="w", bg="#f6fff6", fg="#0a7f2e", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
                tk.Label(row, text=text, anchor="w", bg="#f6fff6", fg="#111", font=("Arial", 11), wraplength=700, justify="left").pack(side=tk.LEFT)

        def save_json():
            data = {
                "name": state["design_name"].get(),
                "habitat_type": state["habitat_type"].get(),
                "launch_system": state["launch_system"].get(),
                "destination": state["destination"].get(),
                "crew_size": int(state["crew_size"].get()),
                "mission_days": int(state["mission_days"].get()),
                "shape": state["shape"].get(),
                "length": float(state["length"].get()),
                "width": float(state["width"].get()),
                "height": float(state["height"].get()),
                "timestamp": datetime.now().isoformat()
            }
            fn = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")],
                                              initialfile=f"{data['name'].replace(' ','_')}.json")
            if fn:
                with open(fn, "w") as f: json.dump(data, f, indent=2)
                messagebox.showinfo("Saved", f"Saved to {fn}")
        tk.Button(frame, text="Save Design JSON", bg="#0074D9", fg="#fff", font=("Arial", 14),
                  command=save_json).pack(pady=10)

    def step4():
        frame = tk.Frame(content, bg="#efefef"); frame.pack(fill=tk.BOTH, expand=True)
        timer_label = tk.Label(frame, text="T-00:05", font=("Arial", 36, "bold"), bg="#efefef"); timer_label.pack(pady=14)
        status_label = tk.Label(frame, text="Press START to run quick checks...", font=("Arial", 16), bg="#efefef"); status_label.pack(pady=6)
        results = tk.Frame(frame, bg="#efefef"); results.pack(pady=6)
        tips = tk.Label(frame, text="", font=("Arial", 14), bg="#efefef", justify="left"); tips.pack(pady=6)
        def run_test():
            if state["testing"]: return
            state["testing"] = True; state["countdown"].set(5); update_timer()
        def update_timer():
            t = state["countdown"].get()
            timer_label.config(text=f"T-00:0{t}" if t>0 else "T-00:00")
            if t > 0:
                wizard.after(1000, lambda: (state["countdown"].set(t-1), update_timer()))
                status_label.config(text="In progress...")
            else:
                status_label.config(text="Results!"); show_results()
        def show_results():
            for w in results.winfo_children(): w.destroy()
            crew = int(state["crew_size"].get())
            vol = max(1.0, state["length"].get()*state["width"].get()*max(1.0, state["height"].get()))
            per_crew = vol/max(1, crew)
            util_score = min(100, int(100 * (per_crew/20.0)))
            power_score = random.randint(70, 95)
            thermal_score = random.randint(65, 92)
            for i, (name, val) in enumerate([("Volume per crew", util_score), ("Power margin", power_score), ("Thermal stability", thermal_score)]):
                tk.Label(results, text=f"{name}: {val}%", font=("Arial", 16, "bold"), bg="#efefef").grid(row=i, column=0, padx=10, pady=5)
                ttk.Progressbar(results, length=300, maximum=100, value=val).grid(row=i, column=1, padx=10, pady=5)
            tips.config(text="- Ensure critical modules exist (Life Support, Power, Medical, Waste)\n- Keep volume per crew > 10 m³; target 20+ m³ for comfort\n- Add Crew Quarters equal to crew size\n- Maintain power margin > 20%")
        tk.Button(frame, text="START", bg="#00bcd4", fg="#fff", font=("Arial", 16, "bold"), command=run_test).pack(pady=8)

    def switch_step(step):
        current_step.set(step)
        for w in content.winfo_children(): w.destroy()
        if step == 1: title.config(text="FIRST STEP"); step1()
        elif step == 2: title.config(text="SHAPE"); step2()
        elif step == 3: title.config(text="SAVE • SHARE"); step3()
        else: title.config(text="TEST"); step4()

    def apply_to_global():
        habitat_config['shape'] = state["shape"].get()
        habitat_config['length'] = float(state["length"].get())
        habitat_config['diameter'] = float(state["width"].get())
        habitat_config['height'] = float(state["height"].get())
        habitat_config['crew_size'] = int(state["crew_size"].get())
        habitat_config['mission_duration'] = int(max(1, state["mission_days"].get() // 30))
        habitat_config['location'] = state["destination"].get()

    tk.Button(nav, text="⟵ Back", font=("Arial", 14),
              command=lambda: switch_step(max(1, current_step.get()-1))).pack(side=tk.LEFT, padx=10)
    tk.Button(nav, text="Next ⟶", font=("Arial", 14),
              command=lambda: switch_step(min(4, current_step.get()+1))).pack(side=tk.RIGHT, padx=10)

    def finish_and_continue():
        apply_to_global()
        messagebox.showinfo("Applied", "Wizard inputs applied. Opening 'Make Your Home in Space'...")
        wizard.destroy()
        open_location_selector()

    tk.Button(nav, text="Finish", font=("Arial", 14, "bold"),
              bg="#00cc66", fg="#fff", command=finish_and_continue).pack(side=tk.RIGHT, padx=10)

    switch_step(1)

# =========================
# MAIN STARTUP WINDOW
# =========================
root = tk.Tk()
root.title("POLIN Space Habitat Designer - NASA Space Apps Challenge 2025")
root.geometry("1280x720")
root.resizable(True, True)
root.bg_image_tk = None

bg_path = os.path.join(script_dir, "Frame 23@2x.png")
rocket_path = os.path.join(script_dir, "Rocket.png")

try:
    bg_image_original = Image.open(bg_path)
    rocket_image_pil = Image.open(rocket_path).resize(ROCKET_SIZE)
    rocket_image = ImageTk.PhotoImage(rocket_image_pil)
    canvas = tk.Canvas(root, highlightthickness=0, bg="black")
    canvas.pack(fill="both", expand=True)
    canvas.bind('<Configure>', resize_background)
except Exception as e:
    print(f"[Warning] Assets could not be loaded: {e}")
    canvas = tk.Canvas(root, highlightthickness=0, bg="#0a0a0f")
    canvas.pack(fill="both", expand=True)

start_button = tk.Button(root, text="Make Your Own Home in Space",
                         command=open_location_selector,
                         bg="#00cc66", fg="white",
                         font=("Arial", 24, "bold"),
                         padx=40, pady=20,
                         relief=tk.RAISED, bd=5)

wizard_button = tk.Button(root, text="Open Wizard",
                          command=open_design_wizard,
                          bg="#0074D9", fg="white",
                          font=("Arial", 18, "bold"),
                          padx=28, pady=12,
                          relief=tk.RAISED, bd=5)

root.mainloop()