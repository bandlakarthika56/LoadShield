import os
import json
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ==========================================
# 1. 8051 MICROCONTROLLER EMULATOR STATE
# ==========================================
emu_state = {
    "PC": 0x0000,
    "A": 0x00,
    "B": 0x00,
    "PSW": 0x00,
    "SP": 0x07,
    "DPTR": 0x0000,
    "R0": 0x00, "R1": 0x00, "R2": 0x00, "R3": 0x00,
    "R4": 0x00, "R5": 0x00, "R6": 0x00, "R7": 0x00,
    "RAM": {f"0x{i:02X}": 0x00 for i in range(128)},
    "Ports": {"P0": 0xFF, "P1": 0xFF, "P2": 0xFF, "P3": 0xFF},
    "Timer0": {"TH0": 0x00, "TL0": 0x00, "TCON": 0x00, "running": False},
    "Interrupts": {"IE": 0x82, "IP": 0x00, "TF0_flag": True, "overload_interrupt_pending": True},
    "trace": []
}

def log_emu(instruction, desc):
    entry = {
        "PC": f"0x{emu_state['PC']:04X}",
        "instruction": instruction,
        "A": f"0x{emu_state['A']:02X}",
        "PSW": f"0x{emu_state['PSW']:02X}",
        "ports": f"P0:{emu_state['Ports']['P0']:02X} P1:{emu_state['Ports']['P1']:02X}",
        "desc": desc,
        "time": datetime.now().strftime("%H:%M:%S. violência")[:-4]
    }
    emu_state["trace"].insert(0, entry)
    if len(emu_state["trace"]) > 25:
        emu_state["trace"].pop()

# ==========================================
# 2. LOADSHIELD SIMULATOR & SCENARIO STATE
# ==========================================
DEFAULT_APPLIANCES = [
    {"id": "app_1", "name": "Medical Oxygen Concentrator", "wattage": 600, "is_on": True, "priority": 1, "category": "Critical"},
    {"id": "app_2", "name": "Hospital Refrigerator", "wattage": 400, "is_on": True, "priority": 2, "category": "Essential"},
    {"id": "app_3", "name": "Smart Facility Lighting", "wattage": 150, "is_on": True, "priority": 3, "category": "Standard"},
    {"id": "app_4", "name": "HVAC Air Conditioner", "wattage": 1500, "is_on": True, "priority": 4, "category": "Comfort"},
    {"id": "app_5", "name": "Industrial Water Heater", "wattage": 1200, "is_on": True, "priority": 4, "category": "Comfort"}
]

sim_state = {
    "appliances": json.loads(json.dumps(DEFAULT_APPLIANCES)),
    "load_limit_w": 2000,
    "status": "Normal",
    "agent_timeline": [],
    "active_tab": "dashboard"
}

def log_agent(stage, message):
    sim_state["agent_timeline"].insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "stage": stage,
        "message": message
    })

def calculate_total_demand():
    return sum(a["wattage"] for a in sim_state["appliances"] if a["is_on"])

# ==========================================
# 3. ROUTES & WEB INTERFACE
# ==========================================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "set_tab":
            sim_state["active_tab"] = request.form.get("tab", "dashboard")
            
        elif action == "reset":
            sim_state["appliances"] = json.loads(json.dumps(DEFAULT_APPLIANCES))
            sim_state["load_limit_w"] = 2000
            sim_state["status"] = "Normal"
            sim_state["agent_timeline"] = []
            emu_state["trace"] = []
            log_agent("RESET", "System state and 8051 emulator restored to default parameters.")
            
        elif action == "scenario_overload":
            sim_state["load_limit_w"] = 1800
            for a in sim_state["appliances"]:
                a["is_on"] = True
            sim_state["status"] = "Overload Active"
            log_agent("SCENARIO", "Severe overload scenario injected. Total demand exceeds threshold.")
            
        elif action == "update_limit":
            try:
                sim_state["load_limit_w"] = int(request.form.get("limit", 2000))
                log_agent("CONFIG", f"Power threshold updated to {sim_state['load_limit_w']}W.")
            except ValueError:
                pass
                
        elif action == "toggle_app":
            aid = request.form.get("aid")
            for a in sim_state["appliances"]:
                if a["id"] == aid:
                    a["is_on"] = not a["is_on"]
                    log_agent("USER", f"Toggled '{a['name']}' to {'ON' if a['is_on'] else 'OFF'}.")
                    
        elif action == "add_app":
            name = request.form.get("name", "").strip()
            try:
                watt = int(request.form.get("watt", 100))
                prio = int(request.form.get("prio", 3))
                if name:
                    new_id = f"app_{len(sim_state['appliances'])+1}"
                    sim_state["appliances"].append({
                        "id": new_id, "name": name, "wattage": watt, "is_on": True, "priority": prio, "category": "Custom"
                    })
                    log_agent("CONFIG", f"Added custom appliance '{name}' ({watt}W, Priority {prio}).")
            except ValueError:
                pass
                
        elif action == "run_agent_loop":
            run_agentic_loop_logic()
            
        elif action == "emulator_step":
            execute_8051_step()

    total_load = calculate_total_demand()
    is_over = total_load > sim_state["load_limit_w"]
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>LoadShield AI | MPMC 8051 Intelligent Load Manager</title>
        <style>
            :root {{
                --bg-main: #0f172a;
                --bg-card: #1e293b;
                --bg-dark: #090d16;
                --accent: #38bdf8;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --danger: #ef4444;
                --success: #22c55e;
                --warning: #f59e0b;
            }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg-main); color: var(--text-main); margin: 0; padding: 20px; }}
            .wrapper {{ max-width: 1200px; margin: auto; }}
            header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; margin-bottom: 20px; }}
            h1 {{ margin: 0; color: var(--accent); font-size: 24px; }}
            .subtitle {{ color: var(--text-muted); font-size: 13px; }}
            
            /* Tabs */
            .tabs {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
            .tab-btn {{ background: var(--bg-card); border: 1px solid #334155; color: var(--text-muted); padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px; }}
            .tab-btn.active {{ background: var(--accent); color: var(--bg-dark); border-color: var(--accent); }}
            
            /* Cards & Metrics */
            .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }}
            .card {{ background: var(--bg-card); padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); border: 1px solid #334155; }}
            .card h3 {{ margin: 0 0 5px 0; font-size: 26px; color: var(--accent); }}
            .card p {{ margin: 0; color: var(--text-muted); font-size: 13px; }}
            
            /* Tables */
            table {{ width: 100%; border-collapse: collapse; background: var(--bg-dark); border-radius: 8px; overflow: hidden; margin-bottom: 20px; }}
            th, td {{ padding: 12px 15px; border-bottom: 1px solid #1e293b; text-align: left; font-size: 14px; }}
            th {{ background: #111827; color: var(--accent); font-weight: 600; }}
            
            /* Buttons & Forms */
            .btn {{ background: #3b82f6; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; }}
            .btn:hover {{ background: #2563eb; }}
            .btn-danger {{ background: var(--danger); }}
            .btn-warning {{ background: var(--warning); color: #000; }}
            .btn-secondary {{ background: #475569; }}
            
            input, select {{ padding: 8px 12px; background: var(--bg-dark); border: 1px solid #475569; color: white; border-radius: 5px; }}
            .panel {{ background: var(--bg-dark); padding: 20px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 20px; }}
            
            /* Logs & Trace */
            .log-box {{ background: var(--bg-dark); padding: 15px; border-radius: 6px; max-height: 250px; overflow-y: auto; font-family: monospace; font-size: 12px; border: 1px solid #334155; }}
            .log-item {{ margin-bottom: 8px; border-bottom: 1px dashed #1e293b; padding-bottom: 6px; }}
            
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
            .badge-on {{ background: var(--success); color: white; }}
            .badge-off {{ background: var(--danger); color: white; }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <header>
                <div>
                    <h1>🛡️ LoadShield AI (8051 MPMC Emulator)</h1>
                    <div class="subtitle">Academic Intelligent Load Management & Deterministic Safety Validator</div>
                </div>
                <div>
                    <form method="POST" style="display:inline;">
                        <input type="hidden" name="action" value="reset">
                        <button type="submit" class="btn btn-secondary">🔄 Factory Reset</button>
                    </form>
                </div>
            </header>

            <!-- Navigation Tabs -->
            <div class="tabs">
                <form method="POST"><input type="hidden" name="action" value="set_tab"><input type="hidden" name="tab" value="dashboard"><button type="submit" class="tab-btn {'active' if sim_state['active_tab']=='dashboard' else ''}">📊 Dashboard</button></form>
                <form method="POST"><input type="hidden" name="action" value="set_tab"><input type="hidden" name="tab" value="simulator"><button type="submit" class="tab-btn {'active' if sim_state['active_tab']=='simulator' else ''}">⚡ Scenario Simulator</button></form>
                <form method="POST"><input type="hidden" name="action" value="set_tab"><input type="hidden" name="tab" value="lab"><button type="submit" class="tab-btn {'active' if sim_state['active_tab']=='lab' else ''}">🧰 8051 Controller Lab</button></form>
                <form method="POST"><input type="hidden" name="action" value="set_tab"><input type="hidden" name="tab" value="activity"><button type="submit" class="tab-btn {'active' if sim_state['active_tab']=='activity' else ''}">🤖 AI Activity Trace</button></form>
                <form method="POST"><input type="hidden" name="action" value="set_tab"><input type="hidden" name="tab" value="reports"><button type="submit" class="tab-btn {'active' if sim_state['active_tab']=='reports' else ''}">📑 Academic Reports</button></form>
            </div>

            <!-- Top Metric Cards -->
            <div class="metrics-grid">
                <div class="card">
                    <h3>{total_load} W</h3>
                    <p>Total Active Demand</p>
                </div>
                <div class="card">
                    <h3>{sim_state['load_limit_w']} W</h3>
                    <p>Configured Power Limit</p>
                </div>
                <div class="card">
                    <h3 style="color: {'var(--danger)' if is_over else 'var(--success)'};">{'OVERLOAD' if is_over else 'NORMAL'}</h3>
                    <p>System Operating State</p>
                </div>
                <div class="card">
                    <h3 style="color: var(--warning); font-size: 18px; margin-top:4px;">{sim_state['status']}</h3>
                    <p>Controller Status</p>
                </div>
            </div>

            <!-- TAB 1: DASHBOARD -->
            { '' if sim_state['active_tab'] != 'dashboard' else f'''
            <div class="panel">
                <h3>⚡ Quick Action & Scenario Control</h3>
                <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-top: 15px;">
                    <form method="POST"><input type="hidden" name="action" value="run_agent_loop"><button type="submit" class="btn">🚀 Run Autonomous Observe-Plan-Act Loop</button></form>
                    <form method="POST"><input type="hidden" name="action" value="scenario_overload"><button type="submit" class="btn btn-warning">⚠️ Inject Severe Overload Scenario</button></form>
                </div>
            </div>

            <h3>Connected Appliance Network</h3>
            <table>
                <tr><th>Appliance Name</th><th>Category</th><th>Wattage</th><th>Priority Tier</th><th>Switch State</th><th>Manual Toggle</th></tr>
                {''.join(f"<tr><td><b>{a['name']}</b></td><td>{a['category']}</td><td>{a['wattage']} W</td><td>Priority {a['priority']}</td><td><span class='badge {\"badge-on\" if a[\"is_on\"] else \"badge-off\"}'>{\"ON\" if a[\"is_on\"] else \"OFF\"}</span></td><td><form method='POST'><input type='hidden' name='action' value='toggle_app'><input type='hidden' name='aid' value='{a[\"id\"]}'><button type='submit' class='btn btn-secondary' style='padding:5px 10px; font-size:12px;'>Toggle</button></form></td></tr>" for a in sim_state['appliances'])}
            </table>
            ''' }

            <!-- TAB 2: SIMULATOR / SCENARIO -->
            { '' if sim_state['active_tab'] != 'simulator' else f'''
            <div class="panel">
                <h3>⚙️ Scenario & Threshold Configuration</h3>
                <form method="POST" style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
                    <input type="hidden" name="action" value="
