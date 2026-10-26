import os
import json
from flask import Flask, render_template_string, request
from datetime import datetime

app = Flask(__name__)

# ==========================================
# 8051 MICROCONTROLLER EMULATOR STATE (PRD Sec 7)
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
    "RAM": {f"0x{i:02X}": 0x00 for i in range(16)},
    "Ports": {"P0": 0xFF, "P1": 0xFD, "P2": 0x00, "P3": 0x82},
    "Timer0": {"TH0": 0xFC, "TL0": 0x18, "TCON": 0x01, "running": True},
    "Interrupts": {"IE": 0x82, "IP": 0x00, "TF0_flag": False, "overload_pending": True},
    "trace": []
}

def log_emu(instruction, desc):
    entry = {
        "PC": f"0x{emu_state['PC']:04X}",
        "instruction": instruction,
        "A": f"0x{emu_state['A']:02X}",
        "desc": desc,
        "time": datetime.now().strftime("%H:%M:%S")
    }
    emu_state["trace"].insert(0, entry)
    if len(emu_state["trace"]) > 20:
        emu_state["trace"].pop()

# ==========================================
# LOAD SIMULATOR STATE (PRD Sec 11)
# ==========================================
DEFAULT_APPLIANCES = [
    {"id": "app_1", "name": "Fan", "wattage": 75, "is_on": True, "priority": 1, "policy": "Essential"},
    {"id": "app_2", "name": "Lights", "wattage": 100, "is_on": True, "priority": 1, "policy": "Essential"},
    {"id": "app_3", "name": "Air conditioner", "wattage": 1200, "is_on": True, "priority": 4, "policy": "Configurable"},
    {"id": "app_4", "name": "Water heater", "wattage": 1000, "is_on": True, "priority": 3, "policy": "Flexible"}
]

sim_state = {
    "appliances": json.loads(json.dumps(DEFAULT_APPLIANCES)),
    "load_limit_w": 2000,
    "status": "Normal",
    "timeline": [],
    "tab": "dashboard"
}

def log_agent(stage, message):
    sim_state["timeline"].insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "stage": stage,
        "message": message
    })

def calculate_demand():
    return sum(a["wattage"] for a in sim_state["appliances"] if a["is_on"])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "tab":
            sim_state["tab"] = request.form.get("val", "dashboard")
        elif action == "reset":
            sim_state["appliances"] = json.loads(json.dumps(DEFAULT_APPLIANCES))
            sim_state["load_limit_w"] = 2000
            sim_state["status"] = "Normal"
            sim_state["timeline"] = []
            emu_state["trace"] = []
            log_agent("RESET", "System state and 8051 emulator restored to defaults.")
        elif action == "overload":
            sim_state["load_limit_w"] = 2000
            for a in sim_state["appliances"]:
                a["is_on"] = True
            sim_state["status"] = "Overload Active"
            log_agent("SCENARIO", "Loaded PRD Demo Scenario (Total: 2,375W, Limit: 2,000W).")
        elif action == "limit":
            try:
                sim_state["load_limit_w"] = int(request.form.get("val", 2000))
                log_agent("CONFIG", f"Demand limit updated to {sim_state['load_limit_w']}W.")
            except ValueError:
                pass
        elif action == "toggle":
            aid = request.form.get("aid")
            for a in sim_state["appliances"]:
                if a["id"] == aid:
                    a["is_on"] = not a["is_on"]
                    log_agent("USER", f"Toggled '{a['name']}' state.")
        elif action == "add":
            name = request.form.get("name", "").strip()
            try:
                watt = int(request.form.get("watt", 100))
                prio = int(request.form.get("prio", 3))
                if name:
                    sim_state["appliances"].append({
                        "id": f"app_{len(sim_state['appliances'])+1}",
                        "name": name,
                        "wattage": watt,
                        "is_on": True,
                        "priority": prio,
                        "policy": "Flexible"
                    })
                    log_agent("CONFIG", f"Added appliance '{name}' ({watt}W).")
            except ValueError:
                pass
        elif action == "run_agent":
            run_agent_loop_logic()
        elif action == "step_emu":
            emu_state["PC"] = (emu_state["PC"] + 2) & 0xFFFF
            emu_state["A"] = 0x3F
            log_emu("MOVX @DPTR, A", "Write power status register to external RAM map.")

    demand = calculate_demand()
    is_over = demand > sim_state["load_limit_w"]

    TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>LoadShield AI | MPMC 8051 Simulator</title>
        <style>
            :root { --bg: #0f172a; --card: #1e293b; --accent: #38bdf8; --text: #f8fafc; --muted: #94a3b8; --danger: #ef4444; --success: #22c55e; --warning: #f59e0b; }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
            .container { max-width: 1150px; margin: auto; background: var(--card); padding: 30px; border-radius: 12px; box-shadow: 0 4px 25px rgba(0,0,0,0.6); border: 1px solid #334155; }
            h1 { color: var(--accent); margin: 0 0 5px 0; text-align: center; font-size: 26px; }
            .sub { text-align: center; color: var(--muted); font-size: 14px; margin-bottom: 25px; }
            
            /* Tabs */
            .tabs { display: flex; gap: 8px; margin-bottom: 25px; flex-wrap: wrap; border-bottom: 1px solid #334155; padding-bottom: 15px; }
            .tab-btn { background: #0f172a; border: 1px solid #334155; color: var(--muted); padding: 10px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }
            .tab-btn.active { background: var(--accent); color: #090d16; border-color: var(--accent); }
            
            /* Metrics */
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }
            .m-box { background: #0f172a; padding: 18px; border-radius: 8px; border: 1px solid #334155; text-align: center; }
            .m-box h3 { margin: 0 0 5px 0; font-size: 24px; color: var(--accent); }
            .m-box p { margin: 0; color: var(--muted); font-size: 13px; }
            
            /* Tables */
            table { width: 100%; border-collapse: collapse; background: #0f172a; border-radius: 8px; overflow: hidden; margin-bottom: 20px; }
            th, td { padding: 12px 16px; border-bottom: 1px solid #1e293b; text-align: left; font-size: 14px; }
            th { background: #111827; color: var(--accent); font-weight: 600; }
            
            /* Buttons & Panels */
            .btn { background: #3b82f6; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; }
            .btn:hover { background: #2563eb; }
            .btn-warning { background: var(--warning); color: #000; }
            .btn-secondary { background: #475569; }
            .panel { background: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 20px; }
            
            .log-box { background: #0f172a; padding: 15px; border-radius: 6px; max-height: 280px; overflow-y: auto; font-family: monospace; font-size: 12px; border: 1px solid #334155; }
            .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
            .badge-on { background: var(--success); color: white; }
            .badge-off { background: var(--danger); color: white; }
            input, select { padding: 8px 12px; background: #0f172a; border: 1px solid #475569; color: white; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ LoadShield AI</h1>
            <div class="sub">Agentic AI + 8051 Microcontroller-Based Intelligent Load Management Simulator (PRD v1.0)[cite: 5]</div>
            
            <!-- Navigation Tabs (PRD Sec 10) -->
            <div class="tabs">
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="dashboard"><button type="submit" class="tab-btn {% if tab == 'dashboard' %}active{% endif %}">📊 Dashboard</button></form>
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="simulator"><button type="submit" class="tab-btn {% if tab == 'simulator' %}active{% endif %}">⚡ Scenario Simulator</button></form>
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="lab"><button type="submit" class="tab-btn {% if tab == 'lab' %}active{% endif %}">🧰 8051 Controller Lab</button></form>
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="activity"><button type="submit" class="tab-btn {% if tab == 'activity' %}active{% endif %}">🤖 AI Activity Timeline</button></form>
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="reports"><button type="submit" class="tab-btn {% if tab == 'reports' %}active{% endif %}">📑 Reports & History</button></form>
                <form method="POST" style="margin-left:auto;"><input type="hidden" name="action" value="reset"><button type="submit" class="btn btn-secondary" style="padding:8px 14px; font-size:12px;">🔄 Factory Reset</button></form>
            </div>

            <!-- Metrics Bar (PRD Sec 10) -->
            <div class="metrics">
                <div class="m-box">
                    <h3>{{ demand }} W</h3>
                    <p>Total Active Demand</p>
                </div>
                <div class="m-box">
                    <h3>{{ limit }} W</h3>
                    <p>Configured Limit</p>
                </div>
                <div class="m-box">
                    <h3 style="color: {% if is_over %}var(--danger){% else %}var(--success){% endif %};">{% if is_over %}OVERLOAD{% else %}NORMAL{% endif %}</h3>
                    <p>System State</p>
                </div>
                <div class="m-box">
                    <h3 style="color: var(--warning); font-size: 16px; margin-top:4px;">{{ status }}</h3>
                    <p>Controller Status</p>
                </div>
            </div>

            <!-- TAB 1: DASHBOARD (PRD Sec 10) -->
            {% if tab == 'dashboard' %}
            <div class="panel">
                <h3>⚡ PRD Demonstration Scenario Control</h3>
                <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-top:10px;">
                    <form method="POST"><input type="hidden" name="action" value="run_agent"><button type="submit" class="btn">🚀 Run Agent Observe-Plan-Act Loop</button></form>
                    <form method="POST"><input type="hidden" name="action" value="overload"><button type="submit" class="btn btn-warning">⚠️ Load PRD Demo Overload Scenario (2,375W)</button></form>
                </div>
            </div>

            <h3>Connected Appliances (PRD Section 11 Demo Model)[cite: 5]</h3>
            <table>
                <tr><th>Appliance</th><th>Power (W)</th><th>Policy / Safety</th><th>Priority</th><th>State</th><th>Manual Toggle</th></tr>
                {% for a in apps %}
                <tr>
                    <td><b>{{ a.name }}</b></td>
                    <td>{{ a.wattage }} W</td>
                    <td>{{ a.policy }}</td>
                    <td>Priority {{ a.priority }}</td>
                    <td><span class="badge {% if a.is_on %}badge-on{% else %}badge-off{% endif %}">{% if a.is_on %}ON{% else %}OFF{% endif %}</span></td>
                    <td>
                        <form method="POST" style="margin:0;"><input type="hidden" name="action" value="toggle"><input type="hidden" name="aid" value="{{ a.id }}"><button type="submit" class="btn btn-secondary" style="padding:5px 10px; font-size:12px;">Toggle</button></form>
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}

            <!-- TAB 2: SCENARIO SIMULATOR (PRD Sec 10) -->
            {% if tab == 'simulator' %}
            <div class="panel">
                <h3>⚙️ Demand Limit & Appliance Configuration</h3>
                <form method="POST" style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
                    <input type="hidden" name="action" value="limit">
                    <label><b>Power Limit Threshold (W):</b></label>
                    <input type="number" name="val" value="{{ limit }}" style="width: 120px;" required>
                    <button type="submit" class="btn">Update Threshold</button>
                </form>

                <h4>+ Add Custom Appliance</h4>
                <form method="POST" style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <input type="hidden" name="action" value="add">
                    <input type="text" name="name" placeholder="Appliance Name" required style="flex:2;">
                    <input type="number" name="watt" placeholder="Wattage (W)" required style="flex:1;">
                    <select name="prio" style="flex:1;">
                        <option value="1">Priority 1 (Essential)</option>
                        <option value="2">Priority 2 (Standard)</option>
                        <option value="3" selected>Priority 3 (Flexible)</option>
                        <option value="4">Priority 4 (Comfort)</option>
                    </select>
                    <button type="submit" class="btn">Add Appliance</button>
                </form>
            </div>
            {% endif %}

            <!-- TAB 3: 8051 CONTROLLER LAB (PRD Sec 7 & 10) -->
            {% if tab == 'lab' %}
            <div class="panel">
                <h3>🧰 8051 Microcontroller Architecture & State Emulator[cite: 5]</h3>
                <p style="color:var(--muted); font-size:13px; margin-bottom:15px;">Models CPU registers, internal RAM, ports, timer progression, and interrupt flags for
