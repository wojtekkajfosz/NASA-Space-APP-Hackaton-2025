import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw
import requests
from io import BytesIO
from datetime import datetime
import random
import os
import json
import math

# =========================
# Module Shape Geometries
# =========================
MODULE_SHAPES = {
    'cube': {
        'params': ['side'],
        'volume_formula': lambda p: p['side']**3,
        'icon': '🟦'
    },
    'cylinder': {
        'params': ['radius', 'height'],
        'volume_formula': lambda p: math.pi * p['radius']**2 * p['height'],
        'icon': '🛢️'
    },
    'sphere': {
        'params': ['radius'],
        'volume_formula': lambda p: (4/3) * math.pi * p['radius']**3,
        'icon': '⚪'
    },
    'hexagonal': {
        'params': ['side', 'height'],
        'volume_formula': lambda p: (3 * math.sqrt(3) / 2) * p['side']**2 * p['height'],
        'icon': '⬡'
    },
    'cone': {
        'params': ['radius', 'height'],
        'volume_formula': lambda p: (1/3) * math.pi * p['radius']**2 * p['height'],
        'icon': '🔺'
    },
    'rectangular': {
        'params': ['length', 'width', 'height'],
        'volume_formula': lambda p: p['length'] * p['width'] * p['height'],
        'icon': '📦'
    },
    'diamond': {
        'params': ['diagonal1', 'diagonal2', 'height'],
        'volume_formula': lambda p: (1/2) * p['diagonal1'] * p['diagonal2'] * p['height'],
        'icon': '💎'
    }
}

# =========================
# Life Support Parameters
# =========================
LIFE_SUPPORT_RATES = {
    'oxygen_consumption': 0.84,  # kg/person/day
    'co2_production': 1.0,  # kg/person/day
    'water_consumption': 3.5,  # liters/person/day
    'power_usage': 100,  # watts/m³
    'heat_generation': 100,  # watts/person
    'waste_production': 0.15  # kg/person/day
}

# =========================
# NASA Module Database
# =========================
NASA_MODULES = {
    'Life Support': {
        'base_volume': 15.2, 
        'color': '#ff6b6b', 
        'icon': '🫁', 
        'category': 'critical',
        'provides': {'oxygen': 10.0, 'co2_removal': 12.0},
        'consumes': {'power': 2000}
    },
    'Waste Management': {
        'base_volume': 8.1, 
        'color': '#8b4513', 
        'icon': '🚽', 
        'category': 'critical',
        'provides': {'waste_processing': 5.0, 'water_recycling': 3.0},
        'consumes': {'power': 800}
    },
    'Thermal Control': {
        'base_volume': 12.5, 
        'color': '#ff8c42', 
        'icon': '🌡️', 
        'category': 'critical',
        'provides': {'cooling': 5000, 'heating': 3000},
        'consumes': {'power': 1500}
    },
    'Communications': {
        'base_volume': 6.2, 
        'color': '#4ecdc4', 
        'icon': '📡', 
        'category': 'operations',
        'provides': {'bandwidth': 100},
        'consumes': {'power': 500}
    },
    'Power Systems': {
        'base_volume': 18.7, 
        'color': '#ffe66d', 
        'icon': '⚡', 
        'category': 'critical',
        'provides': {'power': 10000},
        'consumes': {}
    },
    'Stowage': {
        'base_volume': 25.8, 
        'color': '#a8e6cf', 
        'icon': '📦', 
        'category': 'operations',
        'provides': {'storage': 50},
        'consumes': {}
    },
    'Food Storage': {
        'base_volume': 20.4, 
        'color': '#ff8b94', 
        'icon': '🍽️', 
        'category': 'crew',
        'provides': {'food_capacity': 1000},
        'consumes': {'power': 200}
    },
    'Medical Bay': {
        'base_volume': 16.3, 
        'color': '#ff9a8b', 
        'icon': '🏥', 
        'category': 'critical',
        'provides': {'medical_capacity': 2},
        'consumes': {'power': 600}
    },
    'Crew Quarters': {
        'base_volume': 2.5, 
        'color': '#a8dadc', 
        'icon': '🛏️', 
        'category': 'crew',
        'provides': {'sleeping': 1},
        'consumes': {'power': 50}
    },
    'Exercise Area': {
        'base_volume': 35.2, 
        'color': '#457b9d', 
        'icon': '🏃', 
        'category': 'crew',
        'provides': {'exercise': 4},
        'consumes': {'power': 300}
    },
}

# =========================
# Global Variables
# =========================
placed_modules = []
habitat_config = {
    'shape': 'cylindrical',
    'length': 12,
    'diameter': 8,
    'height': 4,
    'crew_size': 6,
    'mission_duration': 540,
    'location': 'Mars'
}
saved_designs = {}  # Store designs per location
selected_module = None
drag_data = {"x": 0, "y": 0, "item": None}

# =========================
# Utility Functions
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

def calculate_module_volume(module):
    shape = module.get('shape', 'cube')
    params = module.get('geometry', {})
    
    if shape in MODULE_SHAPES and params:
        return MODULE_SHAPES[shape]['volume_formula'](params)
    else:
        return NASA_MODULES[module['name']]['base_volume'] * module.get('scale', 1.0)

def calculate_used_volume():
    return sum(calculate_module_volume(m) for m in placed_modules)

def get_utilization_percentage():
    total = calculate_habitat_volume()
    used = calculate_used_volume()
    return (used / total * 100) if total > 0 else 0

def calculate_life_support():
    crew = habitat_config['crew_size']
    
    required = {
        'oxygen': crew * LIFE_SUPPORT_RATES['oxygen_consumption'],
        'co2_removal': crew * LIFE_SUPPORT_RATES['co2_production'],
        'water': crew * LIFE_SUPPORT_RATES['water_consumption'],
        'power': sum(NASA_MODULES[m['name']]['consumes'].get('power', 0) for m in placed_modules),
        'waste_processing': crew * LIFE_SUPPORT_RATES['waste_production']
    }
    
    provided = {
        'oxygen': sum(NASA_MODULES[m['name']]['provides'].get('oxygen', 0) for m in placed_modules),
        'co2_removal': sum(NASA_MODULES[m['name']]['provides'].get('co2_removal', 0) for m in placed_modules),
        'water_recycling': sum(NASA_MODULES[m['name']]['provides'].get('water_recycling', 0) for m in placed_modules),
        'power': sum(NASA_MODULES[m['name']]['provides'].get('power', 0) for m in placed_modules),
        'waste_processing': sum(NASA_MODULES[m['name']]['provides'].get('waste_processing', 0) for m in placed_modules)
    }
    
    return required, provided

def validate_design():
    issues = []
    crew_size = habitat_config['crew_size']
    
    total_vol = calculate_habitat_volume()
    vol_per_crew = total_vol / crew_size
    if vol_per_crew < 10:
        issues.append(f"⚠️ Volume per crew: {vol_per_crew:.1f} m³ (min: 10 m³)")
    
    critical_systems = ['Life Support', 'Waste Management', 'Medical Bay', 'Power Systems']
    for system in critical_systems:
        if not any(m['name'] == system for m in placed_modules):
            issues.append(f"❌ Missing: {system}")
    
    crew_quarters = sum(m.get('count', 1) for m in placed_modules if m['name'] == 'Crew Quarters')
    if crew_quarters < crew_size:
        issues.append(f"⚠️ Crew Quarters: {crew_quarters}/{crew_size}")
    
    required, provided = calculate_life_support()
    if provided['oxygen'] < required['oxygen']:
        issues.append(f"❌ O₂: {provided['oxygen']:.1f}/{required['oxygen']:.1f} kg/day")
    if provided['power'] < required['power']:
        issues.append(f"❌ Power: {provided['power']:.0f}/{required['power']:.0f} W")
    if provided['co2_removal'] < required['co2_removal']:
        issues.append(f"❌ CO₂: {provided['co2_removal']:.1f}/{required['co2_removal']:.1f} kg/day")
    
    return issues

# =========================
# Module Editor Window
# =========================
def open_module_editor(module, canvas, draw_callback):
    editor = tk.Toplevel()
    editor.title(f"Edit Module: {module['name']}")
    editor.geometry("520x650")
    editor.configure(bg="#1a1a2e")
    
    tk.Label(editor, text=f"📐 {module['name']}", 
             bg="#1a1a2e", fg="#4a9eff", font=("Arial", 18, "bold")).pack(pady=15)
    
    # Shape Selection
    shape_frame = tk.Frame(editor, bg="#16213e", relief=tk.RAISED, bd=2)
    shape_frame.pack(fill=tk.X, padx=20, pady=10)
    
    tk.Label(shape_frame, text="Module Shape:", bg="#16213e", fg="white", 
             font=("Arial", 13, "bold")).pack(anchor=tk.W, padx=10, pady=5)
    
    shape_var = tk.StringVar(value=module.get('shape', 'cube'))
    
    shape_buttons = tk.Frame(shape_frame, bg="#16213e")
    shape_buttons.pack(fill=tk.X, pady=8, padx=5)
    
    param_vars = {}
    param_labels = {}
    
    def update_shape(new_shape):
        shape_var.set(new_shape)
        module['shape'] = new_shape
        
        for widget in shape_buttons.winfo_children():
            if isinstance(widget, tk.Button):
                is_selected = new_shape in widget.cget('text').lower()
                widget.config(bg="#00cc66" if is_selected else "#2a2a3e")
        
        for widget in params_frame.winfo_children()[1:]:
            widget.destroy()
        
        param_vars.clear()
        param_labels.clear()
        
        shape_params = MODULE_SHAPES[new_shape]['params']
        geometry = module.get('geometry', {})
        
        for param in shape_params:
            param_frame = tk.Frame(params_frame, bg="#16213e")
            param_frame.pack(fill=tk.X, pady=6)
            
            tk.Label(param_frame, text=f"{param.capitalize()}:", 
                    bg="#16213e", fg="white", width=12, anchor=tk.W,
                    font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
            
            var = tk.DoubleVar(value=geometry.get(param, 3.0))
            param_vars[param] = var
            
            scale = tk.Scale(param_frame, from_=0.5, to=15.0, resolution=0.1,
                           orient=tk.HORIZONTAL, variable=var, bg="#0074D9", 
                           fg="white", length=250,
                           command=lambda v, p=param: update_param(p, float(v)))
            scale.pack(side=tk.LEFT, padx=5)
            
            label = tk.Label(param_frame, text=f"{var.get():.1f}m", 
                           bg="#16213e", fg="#00ff00", width=7,
                           font=("Courier", 11, "bold"))
            label.pack(side=tk.RIGHT, padx=5)
            param_labels[param] = label
        
        update_volume_display()
    
    def update_param(param, value):
        if 'geometry' not in module:
            module['geometry'] = {}
        module['geometry'][param] = value
        param_labels[param].config(text=f"{value:.1f}m")
        update_volume_display()
        draw_callback()
    
    for shape_name, shape_data in MODULE_SHAPES.items():
        btn = tk.Button(shape_buttons, 
                       text=f"{shape_data['icon']} {shape_name.capitalize()}", 
                       bg="#00cc66" if shape_var.get() == shape_name else "#2a2a3e",
                       fg="white", font=("Arial", 9, "bold"),
                       relief=tk.RAISED, bd=2, padx=8, pady=4,
                       command=lambda s=shape_name: update_shape(s))
        btn.pack(side=tk.LEFT, padx=3, pady=3)
    
    # Geometry Parameters
    params_frame = tk.Frame(editor, bg="#16213e", relief=tk.RAISED, bd=2)
    params_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    tk.Label(params_frame, text="Geometry Parameters (meters):", 
             bg="#16213e", fg="#ffaa00", font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=10, pady=8)
    
    # Volume Display
    volume_frame = tk.Frame(editor, bg="#0a0a0f", relief=tk.RAISED, bd=3)
    volume_frame.pack(fill=tk.X, padx=20, pady=15)
    
    volume_label = tk.Label(volume_frame, text="", bg="#0a0a0f", fg="#00ff00", 
                           font=("Courier", 16, "bold"))
    volume_label.pack(pady=12)
    
    def update_volume_display():
        volume = calculate_module_volume(module)
        volume_label.config(text=f"📦 VOLUME: {volume:.2f} m³")
    
    # Initialize
    update_shape(shape_var.get())
    
    # Buttons
    btn_frame = tk.Frame(editor, bg="#1a1a2e")
    btn_frame.pack(pady=15)
    
    tk.Button(btn_frame, text="✓ Apply & Close", bg="#00cc66", fg="white",
             font=("Arial", 13, "bold"), padx=20, pady=8,
             command=editor.destroy).pack(side=tk.LEFT, padx=5)
    
    tk.Button(btn_frame, text="✗ Cancel", bg="#cc0000", fg="white",
             font=("Arial", 13, "bold"), padx=20, pady=8,
             command=editor.destroy).pack(side=tk.LEFT, padx=5)

# =========================
# Habitat Designer Window
# =========================
def open_habitat_designer(location):
    global habitat_config, selected_module, drag_data, placed_modules, saved_designs
    
    # Load saved design for this location if it exists
    if location in saved_designs:
        placed_modules = saved_designs[location]['modules']
        habitat_config = saved_designs[location]['config'].copy()
    else:
        habitat_config['location'] = location
        placed_modules = []
    
    designer_win = tk.Toplevel()
    designer_win.title(f"🚀 NASA Habitat Designer - {location}")
    designer_win.geometry("1650x950")
    designer_win.configure(bg="#1a1a2e")
    
    # LEFT PANEL
    left_frame = tk.Frame(designer_win, bg="#16213e", width=340)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
    left_frame.pack_propagate(False)
    
    tk.Label(left_frame, text="⚙️ Habitat Configuration", 
             bg="#16213e", fg="#4a9eff", font=("Arial", 15, "bold")).pack(pady=12)
    
    tk.Label(left_frame, text="Habitat Shape:", bg="#16213e", fg="white",
             font=("Arial", 11, "bold")).pack(pady=5)
    shape_var = tk.StringVar(value=habitat_config['shape'])
    shapes = ['cylindrical', 'spherical', 'dome', 'modular']
    for shape in shapes:
        tk.Radiobutton(left_frame, text=shape.capitalize(), variable=shape_var, 
                      value=shape, bg="#16213e", fg="white", selectcolor="#0074D9",
                      font=("Arial", 10),
                      command=lambda: update_config('shape', shape_var.get())).pack(anchor=tk.W, padx=25)
    
    tk.Label(left_frame, text="\n📏 Dimensions (meters)", 
             bg="#16213e", fg="#4a9eff", font=("Arial", 12, "bold")).pack()
    
    def create_slider(label, key, from_, to, default):
        frame = tk.Frame(left_frame, bg="#16213e")
        frame.pack(fill=tk.X, padx=15, pady=6)
        tk.Label(frame, text=label, bg="#16213e", fg="white", width=13, 
                anchor=tk.W, font=("Arial", 10)).pack(side=tk.LEFT)
        var = tk.DoubleVar(value=default)
        slider = tk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL, 
                         variable=var, bg="#0074D9", fg="white",
                         command=lambda v: update_config(key, float(v)))
        slider.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        return var
    
    length_var = create_slider("Length:", "length", 3, 50, habitat_config['length'])
    diameter_var = create_slider("Diameter:", "diameter", 3, 30, habitat_config['diameter'])
    height_var = create_slider("Height:", "height", 2, 20, habitat_config['height'])
    
    tk.Label(left_frame, text="\n👥 Mission Parameters", 
             bg="#16213e", fg="#4a9eff", font=("Arial", 12, "bold")).pack()
    
    crew_var = create_slider("Crew Size:", "crew_size", 1, 20, habitat_config['crew_size'])
    duration_var = create_slider("Duration (days):", "mission_duration", 30, 1800, habitat_config['mission_duration'])
    
    # Stats Display
    stats_frame = tk.Frame(left_frame, bg="#0a0a0f", relief=tk.RAISED, bd=2)
    stats_frame.pack(fill=tk.BOTH, padx=12, pady=12, expand=True)
    
    stats_label = tk.Label(stats_frame, text="", bg="#0a0a0f", fg="#4a9eff", 
                          font=("Courier", 9), justify=tk.LEFT)
    stats_label.pack(padx=8, pady=8)
    
    def update_stats():
        total_vol = calculate_habitat_volume()
        used_vol = calculate_used_volume()
        util = get_utilization_percentage()
        vol_per_crew = total_vol / habitat_config['crew_size']
        
        required, provided = calculate_life_support()
        
        o2_status = "✓" if provided['oxygen'] >= required['oxygen'] else "✗"
        co2_status = "✓" if provided['co2_removal'] >= required['co2_removal'] else "✗"
        pwr_status = "✓" if provided['power'] >= required['power'] else "✗"
        
        stats_text = f"""HABITAT STATISTICS
==================
Total Volume:  {total_vol:.1f} m³
Used Volume:   {used_vol:.1f} m³
Utilization:   {util:.1f}%
Volume/Crew:   {vol_per_crew:.1f} m³

Crew:          {habitat_config['crew_size']}
Duration:      {habitat_config['mission_duration']} mo
Modules:       {len(placed_modules)}

LIFE SUPPORT SYSTEMS
==================
{o2_status} O₂:  {provided['oxygen']:.1f}/{required['oxygen']:.1f} kg/d
{co2_status} CO₂: {provided['co2_removal']:.1f}/{required['co2_removal']:.1f} kg/d
  H₂O: {provided.get('water_recycling', 0):.1f}/{required['water']:.1f} L/d
{pwr_status} PWR: {provided['power']:.0f}/{required['power']:.0f} W
  WST: {provided['waste_processing']:.1f}/{required['waste_processing']:.1f} kg/d
        """
        stats_label.config(text=stats_text)
        designer_win.after(1000, update_stats)
    
    update_stats()
    
    # CENTER PANEL
    center_frame = tk.Frame(designer_win, bg="#0a0a0f")
    center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    tk.Label(center_frame, text="🛠️ Habitat Layout Designer", 
             bg="#0a0a0f", fg="#4a9eff", font=("Arial", 17, "bold")).pack(pady=8)
    tk.Label(center_frame, text="Drag to move • Double-click to edit shape & size", 
             bg="#0a0a0f", fg="#ffaa00", font=("Arial", 11, "italic")).pack()
    
    canvas = tk.Canvas(center_frame, bg="#1a1a2e", width=850, height=750)
    canvas.pack(padx=10, pady=10)
    
    # Canvas handlers
    def on_module_press(event):
        global selected_module, drag_data
        x, y = event.x, event.y
        
        for module in reversed(placed_modules):
            mx, my = module['x'], module['y']
            volume = calculate_module_volume(module)
            size = math.sqrt(volume) * 4
            
            if abs(x - mx) < size/2 and abs(y - my) < size/2:
                selected_module = module
                drag_data = {"x": x, "y": y, "item": module}
                canvas.config(cursor="fleur")
                break
    
    def on_module_drag(event):
        global drag_data
        if drag_data["item"]:
            dx = event.x - drag_data["x"]
            dy = event.y - drag_data["y"]
            
            drag_data["item"]['x'] += dx
            drag_data["item"]['y'] += dy
            
            drag_data["x"] = event.x
            drag_data["y"] = event.y
            
            draw_modules()
    
    def on_module_release(event):
        global drag_data, selected_module
        drag_data = {"x": 0, "y": 0, "item": None}
        canvas.config(cursor="")
    
    def on_module_double_click(event):
        x, y = event.x, event.y
        
        for module in reversed(placed_modules):
            mx, my = module['x'], module['y']
            volume = calculate_module_volume(module)
            size = math.sqrt(volume) * 4
            
            if abs(x - mx) < size/2 and abs(y - my) < size/2:
                open_module_editor(module, canvas, draw_modules)
                break
    
    def on_right_click(event):
        x, y = event.x, event.y
        
        for i, module in enumerate(reversed(placed_modules)):
            mx, my = module['x'], module['y']
            volume = calculate_module_volume(module)
            size = math.sqrt(volume) * 4
            
            if abs(x - mx) < size/2 and abs(y - my) < size/2:
                if messagebox.askyesno("Remove Module", 
                                      f"Remove {module['name']}?"):
                    placed_modules.remove(module)
                    draw_modules()
                break
    
    canvas.bind("<Button-1>", on_module_press)
    canvas.bind("<B1-Motion>", on_module_drag)
    canvas.bind("<ButtonRelease-1>", on_module_release)
    canvas.bind("<Double-Button-1>", on_module_double_click)
    canvas.bind("<Button-3>", on_right_click)
    
    def draw_habitat():
        canvas.delete("all")
        for i in range(0, 850, 20):
            canvas.create_line(i, 0, i, 750, fill="#2a2a3e", dash=(2, 4))
        for i in range(0, 750, 20):
            canvas.create_line(0, i, 850, i, fill="#2a2a3e", dash=(2, 4))
        
        scale = min(650 / habitat_config['length'], 550 / habitat_config['diameter'])
        w = habitat_config['length'] * scale
        h = habitat_config['diameter'] * scale
        x1 = (850 - w) / 2
        y1 = (750 - h) / 2
        
        canvas.create_rectangle(x1, y1, x1 + w, y1 + h, 
                               outline="#4a9eff", width=4, dash=(12, 6))
        canvas.create_text(425, 35, 
                          text=f"{location} Habitat: {habitat_config['shape'].capitalize()}", 
                          fill="#4a9eff", font=("Arial", 15, "bold"))
    
    draw_habitat()
    
    def draw_modules():
        draw_habitat()
        
        for module in placed_modules:
            mod_data = NASA_MODULES[module['name']]
            volume = calculate_module_volume(module)
            size = math.sqrt(volume) * 4
            x, y = module['x'], module['y']
            
            shape = module.get('shape', 'cube')
            
            if shape == 'cube' or shape == 'rectangular':
                canvas.create_rectangle(x - size/2, y - size/2, 
                                       x + size/2, y + size/2,
                                       fill=mod_data['color'], outline="white", width=2)
            elif shape == 'cylinder':
                canvas.create_oval(x - size/2, y - size/3, 
                                  x + size/2, y + size/3,
                                  fill=mod_data['color'], outline="white", width=2)
            elif shape == 'sphere':
                canvas.create_oval(x - size/2, y - size/2, 
                                  x + size/2, y + size/2,
                                  fill=mod_data['color'], outline="white", width=2)
            elif shape == 'hexagonal':
                points = []
                for i in range(6):
                    angle = math.pi / 3 * i
                    px = x + size/2 * math.cos(angle)
                    py = y + size/2 * math.sin(angle)
                    points.extend([px, py])
                canvas.create_polygon(points, fill=mod_data['color'], 
                                    outline="white", width=2)
            elif shape == 'cone' or shape == 'diamond':
                points = [x, y - size/2, x + size/2, y + size/2, 
                         x - size/2, y + size/2]
                canvas.create_polygon(points, fill=mod_data['color'], 
                                    outline="white", width=2)
            else:
                canvas.create_rectangle(x - size/2, y - size/2, 
                                       x + size/2, y + size/2,
                                       fill=mod_data['color'], outline="white", width=2)
            
            canvas.create_text(x, y - 12, text=mod_data['icon'], 
                             fill="white", font=("Arial", 16))
            canvas.create_text(x, y + 12, 
                             text=f"{module['name']}\n{volume:.1f}m³", 
                             fill="white", font=("Arial", 8, "bold"))
    
    # RIGHT PANEL
    right_frame = tk.Frame(designer_win, bg="#16213e", width=400)
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
    right_frame.pack_propagate(False)
    
    tk.Label(right_frame, text="📦 Module Library", 
             bg="#16213e", fg="#4a9eff", font=("Arial", 15, "bold")).pack(pady=12)
    
    canvas_frame = tk.Frame(right_frame, bg="#16213e")
    canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    module_canvas = tk.Canvas(canvas_frame, bg="#16213e", 
                             yscrollcommand=scrollbar.set)
    module_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=module_canvas.yview)
    
    module_frame = tk.Frame(module_canvas, bg="#16213e")
    module_canvas.create_window((0, 0), window=module_frame, anchor=tk.NW)
    
    def add_module(module_name):
        module_data = NASA_MODULES[module_name]
        new_module = {
            'name': module_name,
            'count': 1,
            'x': random.randint(250, 600),
            'y': random.randint(250, 500),
            'shape': 'cube',
            'geometry': {'side': 3.0}
        }
        placed_modules.append(new_module)
        draw_modules()
        messagebox.showinfo("✓ Module Added", 
                           f"{module_name} added!\n\nDouble-click to edit shape & size\nRight-click to remove")
    
    for module_name, module_data in NASA_MODULES.items():
        btn_frame = tk.Frame(module_frame, bg="#0a0a0f", relief=tk.RAISED, bd=2)
        btn_frame.pack(fill=tk.X, pady=4, padx=5)
        
        icon_label = tk.Label(btn_frame, text=module_data['icon'], bg="#0a0a0f", 
                             fg=module_data['color'], font=("Arial", 18))
        icon_label.pack(side=tk.LEFT, padx=8, pady=5)
        
        info_frame = tk.Frame(btn_frame, bg="#0a0a0f")
        info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(info_frame, text=module_name, bg="#0a0a0f", fg="white", 
                font=("Arial", 11, "bold")).pack(anchor=tk.W)
        tk.Label(info_frame, text=f"Base: {module_data['base_volume']} m³", 
                bg="#0a0a0f", fg="#888", font=("Arial", 8)).pack(anchor=tk.W)
        
        # Show what it provides
        provides_text = ", ".join([f"{k}: {v}" for k, v in module_data['provides'].items()][:2])
        if provides_text:
            tk.Label(info_frame, text=f"⚡ {provides_text}", 
                    bg="#0a0a0f", fg="#4ecdc4", font=("Arial", 7)).pack(anchor=tk.W)
        
        add_btn = tk.Button(btn_frame, text="+", bg="#00cc66", fg="white",
                           font=("Arial", 16, "bold"), width=3,
                           command=lambda m=module_name: add_module(m))
        add_btn.pack(side=tk.RIGHT, padx=8, pady=5)
    
    module_frame.update_idletasks()
    module_canvas.config(scrollregion=module_canvas.bbox("all"))
    
    # Control Buttons
    control_frame = tk.Frame(right_frame, bg="#16213e")
    control_frame.pack(fill=tk.X, padx=10, pady=10)
    
    def check_validation():
        issues = validate_design()
        if not issues:
            messagebox.showinfo("✓ Design Valid", 
                              "Excellent! Your habitat design meets NASA requirements!\n\n" +
                              "All critical systems present and life support adequate.")
        else:
            messagebox.showwarning("⚠️ Design Issues", 
                                  "Issues found:\n\n" + "\n".join(issues) +
                                  "\n\nAdd missing modules or increase their capacity.")
    
    validate_btn = tk.Button(control_frame, text="✓ Validate Design", 
                            bg="#00cc66", fg="white", font=("Arial", 12, "bold"),
                            command=check_validation)
    validate_btn.pack(pady=5, fill=tk.X)
    
    def export_design():
        design_data = {
            'habitat': habitat_config,
            'modules': placed_modules,
            'statistics': {
                'total_volume': calculate_habitat_volume(),
                'used_volume': calculate_used_volume(),
                'utilization': get_utilization_percentage()
            },
            'life_support': {
                'required': calculate_life_support()[0],
                'provided': calculate_life_support()[1]
            }
        }
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"habitat_{location}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        )
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(design_data, f, indent=2)
            messagebox.showinfo("💾 Saved", f"Design exported to:\n{filename}")
    
    export_btn = tk.Button(control_frame, text="💾 Export Design", 
                          bg="#0074D9", fg="white", font=("Arial", 12, "bold"),
                          command=export_design)
    export_btn.pack(pady=5, fill=tk.X)
    
    def clear_all():
        if messagebox.askyesno("🗑️ Clear All", "Remove all modules?"):
            placed_modules.clear()
            draw_habitat()
    
    clear_btn = tk.Button(control_frame, text="🗑️ Clear All", 
                         bg="#cc0000", fg="white", font=("Arial", 12, "bold"),
                         command=clear_all)
    clear_btn.pack(pady=5, fill=tk.X)
    
    def update_config(key, value):
        habitat_config[key] = value
        draw_habitat()

# =========================
# GIF Animation Functions
# =========================
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
# NASA Image Windows
# =========================
def open_apod_window(location):
    global root, label, text_label
    root.destroy()
    root = tk.Tk()
    root.title(f"{location} - NASA Space Apps Challenge")
    root.configure(bg="#222")
    root.geometry("900x900")

    label = tk.Label(root, bg="#222")
    label.place(x=0, y=0)

    text_label = tk.Label(root, text="", bg="#222", fg="#fff", font=("Arial", 18))
    text_label.place(x=0, y=700)

    if location == "Moon":
        set_moon_background()
    elif location == "Outer Space":
        set_apod_background()
        generate_btn = tk.Button(
            root, text="Generate new image", command=lambda: set_apod_background(),
            bg="#0074D9", fg="#fff", font=("Arial", 14), relief=tk.RAISED, padx=20, pady=5
        )
        generate_btn.place(x=0, y=750)
    elif location == "Mars":
        set_mars_background()

    designer_btn = tk.Button(
        root, text="🛠️ Design Habitat", 
        command=lambda: open_habitat_designer(location),
        bg="#00cc66", fg="#fff", font=("Arial", 16, "bold"), 
        relief=tk.RAISED, padx=30, pady=10
    )
    designer_btn.place(x=300, y=750)

    open_second_btn = tk.Button(
        root, text="Open Second Window", command=open_second_window,
        bg="#0074D9", fg="#fff", font=("Arial", 14), relief=tk.RAISED, padx=20, pady=5
    )
    open_second_btn.place(x=0, y=800)

    close_button = tk.Button(
        root, text="Close", command=root.destroy,
        bg="#444", fg="#fff", font=("Arial", 14), relief=tk.RAISED, padx=20, pady=5
    )
    close_button.place(x=0, y=850)

    if location == "Outer Space":
        tk.Button(root, text="Go to: Moon", command=lambda: open_apod_window("Moon"),
                 bg="#0074D9", fg="#fff", font=("Arial", 12)).place(x=750, y=850)
        tk.Button(root, text="Go to: Mars", command=lambda: open_apod_window("Mars"),
                 bg="#0074D9", fg="#fff", font=("Arial", 12)).place(x=830, y=850)
    elif location == "Moon":
        tk.Button(root, text="Go to: Mars", command=lambda: open_apod_window("Mars"),
                 bg="#0074D9", fg="#fff", font=("Arial", 12)).place(x=750, y=850)
        tk.Button(root, text="Go to: Outer Space", command=lambda: open_apod_window("Outer Space"),
                 bg="#0074D9", fg="#fff", font=("Arial", 12)).place(x=830, y=850)
    elif location == "Mars":
        tk.Button(root, text="Go to: Moon", command=lambda: open_apod_window("Moon"),
                 bg="#0074D9", fg="#fff", font=("Arial", 12)).place(x=750, y=850)
        tk.Button(root, text="Go to: Outer Space", command=lambda: open_apod_window("Outer Space"),
                 bg="#0074D9", fg="#fff", font=("Arial", 12)).place(x=830, y=850)

    root.mainloop()

def open_second_window():
    second_win = tk.Toplevel(root)
    second_win.title("Second Window")
    second_win.configure(bg="#0074D9")
    second_win.geometry("400x300")
    close_btn = tk.Button(
        second_win, text="Close", command=second_win.destroy,
        bg="#444", fg="#fff", font=("Arial", 14), relief=tk.RAISED, padx=20, pady=5
    )
    close_btn.pack(expand=True)

def set_apod_background():
    global label, text_label
    start_date = datetime(2015, 1, 1)
    end_date = datetime.now()
    random_date = start_date + (end_date - start_date) * random.random()
    current_date = random_date.strftime("%Y-%m-%d")
    api_url = f"https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY&date={current_date}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("media_type") == "image":
            img_url = data["url"]
            img_response = requests.get(img_url, timeout=10)
            img_response.raise_for_status()
            img_data = img_response.content

            if img_url.endswith(".gif"):
                frames = load_gif_frames(BytesIO(img_data), size=(900, 700))
                if frames:
                    animate_gif(label, frames, delay=120)
            else:
                img = Image.open(BytesIO(img_data))
                img.thumbnail((900, 700))
                photo = ImageTk.PhotoImage(img)
                label.config(image=photo)
                label.image = photo

            text_label.config(text=f"NASA Picture of day: {data.get('date', current_date)}")
        else:
            text_label.config(text=f"No image available for {current_date}")
    except requests.RequestException as e:
        text_label.config(text=f"Error fetching APOD: {str(e)}")

def set_moon_background():
    global label, text_label
    moon_url = "https://images-assets.nasa.gov/image/PIA00405/PIA00405~large.jpg"
    try:
        img_response = requests.get(moon_url, timeout=10)
        img_response.raise_for_status()
        img_data = img_response.content
        img = Image.open(BytesIO(img_data))
        img.thumbnail((900, 700))
        photo = ImageTk.PhotoImage(img)
        label.config(image=photo)
        label.image = photo
        text_label.config(text="NASA Moon Image")
    except requests.RequestException as e:
        text_label.config(text=f"Error fetching Moon image: {str(e)}")

def set_mars_background():
    global label, text_label
    mars_url = "https://mars.nasa.gov/msl-raw-images/msss/01000/mcam/1000ML0044631300305227E03_DXXX.jpg"
    try:
        img_response = requests.get(mars_url, timeout=10)
        img_response.raise_for_status()
        img_data = img_response.content
        img = Image.open(BytesIO(img_data))
        img.thumbnail((900, 700))
        photo = ImageTk.PhotoImage(img)
        label.config(image=photo)
        label.image = photo
        text_label.config(text="NASA Mars Image")
    except requests.RequestException as e:
        text_label.config(text=f"Error fetching Mars image: {str(e)}")

def select_location(location):
    if location in ["Moon", "Outer Space", "Mars"]:
        open_apod_window(location)

# =========================
# MAIN STARTUP WINDOW
# =========================
root = tk.Tk()
root.title("🚀 Polin Space Society - NASA Space Apps Challenge 2025")
root.configure(bg="#222")
root.geometry("600x500")

title_label = tk.Label(root, text="POLIN SPACE SOCIETY", 
                       bg="#222", fg="#4a9eff", font=("Arial", 24, "bold"))
title_label.pack(pady=10)

subtitle_label = tk.Label(root, text="NASA Space Apps Challenge 2025\nHabitat Layout Creator", 
                          bg="#222", fg="#fff", font=("Arial", 14))
subtitle_label.pack(pady=5)

question_label = tk.Label(root, text="Where do You want to build Your space habitat?",
                          bg="#222", fg="#fff", font=("Arial", 16))
question_label.pack(pady=20)

button_frame = tk.Frame(root, bg="#222")
button_frame.pack(pady=10)

script_dir = os.path.dirname(os.path.abspath(__file__))

outer_space_frames = load_gif_frames(os.path.join(script_dir, "OuterSpace.gif"), size=(100, 100))
moon_frames = load_gif_frames(os.path.join(script_dir, "Moon.gif"), size=(100, 100))
mars_frames = load_gif_frames(os.path.join(script_dir, "MARS.gif"), size=(100, 100))

outer_space_label = tk.Label(button_frame, bg="#222")
outer_space_label.grid(row=0, column=0, padx=20, pady=10)
if outer_space_frames:
    animate_gif(outer_space_label, outer_space_frames, delay=120)

outer_space_btn = tk.Button(button_frame, text="Outer Space",
                            command=lambda: select_location("Outer Space"),
                            bg="#0074D9", fg="#fff", font=("Arial", 12))
outer_space_btn.grid(row=1, column=0)

moon_label = tk.Label(button_frame, bg="#222")
moon_label.grid(row=0, column=1, padx=20, pady=10)
if moon_frames:
    animate_gif(moon_label, moon_frames, delay=120)

moon_btn = tk.Button(button_frame, text="Moon",
                     command=lambda: select_location("Moon"),
                     bg="#0074D9", fg="#fff", font=("Arial", 12))
moon_btn.grid(row=1, column=1)

mars_label = tk.Label(button_frame, bg="#222")
mars_label.grid(row=0, column=2, padx=20, pady=10)
if mars_frames:
    animate_gif(mars_label, mars_frames, delay=120)

mars_btn = tk.Button(button_frame, text="Mars",
                     command=lambda: select_location("Mars"),
                     bg="#0074D9", fg="#fff", font=("Arial", 12))
mars_btn.grid(row=1, column=2)

team_label = tk.Label(root, text="International Team from 7 countries", 
                      bg="#222", fg="#4a9eff", font=("Arial", 12))
team_label.pack(pady=20)

root.mainloop()