import os
import json
from flask import Flask, render_template_string, request
from datetime import datetime

app = Flask(__name__)

emu_state = {
    "PC": 0x0000,
    "A": 0x00,
    "B": 0x00,
    "PSW": 0x00,
    "SP": 0x07,
    "DPTR": 0x0000,
    "Ports": {"P0": 0xFF, "P1": 0xFF, "P2": 0xFF, "P3": 0xFF},
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
    "timeline": [],
    "tab": "dashboard"
}

def log_agent(stage, message):
    sim_state["timeline"].insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "stage": stage,
        "message": message
    })

def total_load():
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
            log_agent("RESET", "Restored system defaults.")
        elif action == "overload":
            sim_state["load_limit_w"] = 1800
            for a in sim_state["appliances"]:
                a["is_on"] = True
            sim_state["status"] = "Overload Active"
            log_agent("SCENARIO", "Injected severe overload scenario.")
        elif action == "limit":
            try:
                sim_state["load_limit_w"] = int(request.form.get("val", 2000))
                log_agent("CONFIG", f"Limit updated to {sim_state['load_limit_w']}W.")
            except ValueError:
                pass
        elif action == "toggle":
            aid = request.form.get("aid")
            for a in sim_state["appliances"]:
                if a["id"] == aid:
                    a["is_on"] = not a["is_on"]
                    log_agent("USER", f"Toggled '{a['name']}'.")
        elif action == "add":
            name = request.form.get("name", "").strip()
            try:
                watt = int(request.form.get("watt", 100))
                prio = int(request.form.get("prio", 3))
                if name:
                    sim_state["appliances"].append({"id": f"app_{len(sim_state['appliances'])+1}", "name": name, "wattage": watt, "is_on": True, "priority": prio, "category": "Custom"})
                    log_agent("CONFIG", f"Added '{name}' ({watt}W, P{prio}).")
            except ValueError:
                pass
        elif action == "run_agent":
            run_agent_logic()
        elif action == "step_emu":
            emu_state["PC"] = (emu_state["PC"] + 2) & 0xFFFF
            log_emu("MOVX @DPTR, A", "Write control register to RAM memory map.")

    load = total_load()
    is_over = load > sim_state["load_limit_w"]
    
    TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LoadShield AI | MPMC 8051 Simulator</title>
        <style>
            body { font-family: sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
            .box { max-width: 1100px; margin: auto; background: #1e293b; padding: 25px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
            h1 { color: #38bdf8; margin: 0 0 5px 0; text-align: center; }
            .sub { text-align: center; color: #94a3b8; font-size: 13px; margin-bottom: 20px; }
            .tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
            .tab { background: #0f172a; border: 1px solid #334155; color: #94a3b8; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; }
            .tab.active { background: #38bdf8; color: #0f172a; border-color: #38bdf8; }
            .metrics { display: flex; justify-content: space-around; background: #0f172a; padding: 15px; border-radius: 6px; margin-bottom: 20px; text-align: center; }
            table { width: 100%; border-collapse: collapse; background: #0f172a; border-radius: 6px; overflow: hidden; margin-bottom: 20px; }
            th, td { padding: 12px 15px; border-bottom: 1px solid #1e293b; text-align: left; font-size: 14px; }
            th { background: #111827; color: #38bdf8; }
            .btn { background: #3b82f6; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: bold; }
            .btn-warning { background: #f59e0b; color: #000; }
            .btn-secondary { background: #475569; }
            .panel { background: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 20px; }
            .log-box { background: #0f172a; padding: 15px; border-radius: 6px; max-height: 250px; overflow-y: auto; font-family: monospace; font-size: 12px; border: 1px solid #334155; }
            .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
            .badge-on { background: #22c55e; color: white; }
            .badge-off { background: #ef4444; color: white; }
            input, select { padding: 8px 12px; background: #0f172a; border: 1px solid #475569; color: white; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🛡️ LoadShield AI (8051 MPMC Simulator)</h1>
            <div class="sub">Academic Intelligent Load Management & Deterministic Safety Validator</div>
            
            <div class="tabs">
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="dashboard"><button type="submit" class="tab {% if tab == 'dashboard' %}active{% endif %}">📊 Dashboard</button></form>
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="simulator"><button type="submit" class="tab {% if tab == 'simulator' %}active{% endif %}">⚡ Scenario Simulator</button></form>
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="lab"><button type="submit" class="tab {% if tab == 'lab' %}active{% endif %}">🧰 8051 Controller Lab</button></form>
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="activity"><button type="submit" class="tab {% if tab == 'activity' %}active{% endif %}">🤖 AI Activity Trace</button></form>
                <form method="POST"><input type="hidden" name="action" value="tab"><input type="hidden" name="val" value="reports"><button type="submit" class="tab {% if tab == 'reports' %}active{% endif %}">📑 Academic Report</button></form>
                <form method="POST" style="margin-left:auto;"><input type="hidden" name="action" value="reset"><button type="submit" class="btn btn-secondary">🔄 Reset</button></form>
            </div>

            <div class="metrics">
                <div><h3>{{ load }} W</h3><p>Total Active Demand</p></div>
                <div><h3>{{ limit }} W</h3><p>Configured Limit</p></div>
                <div><h3 style="color: {% if is_over %}#ef4444{% else %}#22c55e{% endif %};">{% if is_over %}OVERLOAD{% else %}NORMAL{% endif %}</h3><p>System State</p></div>
                <div><h3 style="color: #f59e0b; font-size: 16px; margin-top:5px;">{{ status }}</h3><p>Controller Status</p></div>
            </div>

            {% if tab == 'dashboard' %}
            <div class="panel">
                <h3>⚡ Quick Actions</h3>
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <form method="POST"><input type="hidden" name="action" value="run_agent"><button type="submit" class="btn">🚀 Run AI Agent Loop</button></form>
                    <form method="POST"><input type="hidden" name="action" value="overload"><button type="submit" class="btn btn-warning">⚠️ Inject Overload Scenario</button></form>
                </div>
            </div>
            <h3>Connected Appliances</h3>
            <table>
                <tr><th>Name</th><th>Category</th><th>Wattage</th><th>Priority</th><th>State</th><th>Action</th></tr>
                {% for a in apps %}
                <tr>
                    <td><b>{{ a.name }}</b></td>
                    <td>{{ a.category }}</td>
                    <td>{{ a.wattage }} W</td>
                    <td>Priority {{ a.priority }}</td>
                    <td><span class="badge {% if a.is_on %}badge-on{% else %}badge-off{% endif %}">{% if a.is_on %}ON{% else %}OFF{% endif %}</span></td>
                    <td>
                        <form method="POST" style="margin:0;"><input type="hidden" name="action" value="toggle"><input type="hidden" name="aid" value="{{ a.id }}"><button type="submit" class="btn btn-secondary" style="padding:5px 10px; font-size:12px;">Toggle</button></form>
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}

            {% if tab == 'simulator' %}
            <div class="panel">
                <h3>⚙️ Scenario Configuration</h3>
                <form method="POST" style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
                    <input type="hidden" name="action" value="limit">
                    <label><b>Power Limit (W):</b></label>
                    <input type="number" name="val" value="{{ limit }}" style="width: 120px;" required>
                    <button type="submit" class="btn">Update Limit</button>
                </form>
                <h4>+ Add Custom Appliance</h4>
                <form method="POST" style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <input type="hidden" name="action" value="add">
                    <input type="text" name="name" placeholder="Appliance Name" required style="flex:2;">
                    <input type="number" name="watt" placeholder="Wattage (W)" required style="flex:1;">
                    <select name="prio" style="flex:1;">
                        <option value="1">P1 (Critical)</option>
                        <option value="2">P2 (Essential)</option>
                        <option value="3">P3 (Standard)</option>
                        <option value="4" selected>P4 (Comfort)</option>
                    </select>
                    <button type="submit" class="btn">Add Device</button>
                </form>
            </div>
            {% endif %}

            {% if tab == 'lab' %}
            <div class="panel">
                <h3>🧰 8051 Microcontroller Architecture & State</h3>
                <form method="POST" style="margin-bottom: 20px;"><input type="hidden" name="action" value="step_emu"><button type="submit" class="btn">▶ Step 8051 Instruction</button></form>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px; margin-bottom:20px;">
                    <div style="background:#090d16; padding:15px; border-radius:6px; border:1px solid #334155;">
                        <h4 style="margin-top:0; color:#38bdf8;">CPU Registers</h4>
                        <p><b>PC:</b> 0x{{"%04X"|format(emu.PC)}} | <b>SP:</b> 0x{{"%02X"|format(emu.SP)}}</p>
                        <p><b>A:</b> 0x{{"%02X"|format(emu.A)}} | <b>B:</b> 0x{{"%02X"|format(emu.B)}}</p>
                    </div>
                    <div style="background:#090d16; padding:15px; border-radius:6px; border:1px solid #334155;">
                        <h4 style="margin-top:0; color:#38bdf8;">GPIO Port Mapping</h4>
                        <p><b>P0 (Relays):</b> 0x{{"%02X"|format(emu.Ports.P0)}}</p>
                        <p><b>P1 (Sensors):</b> 0x{{"%02X"|format(emu.Ports.P1)}}</p>
                    </div>
                </div>
                <h3>Instruction Trace Log</h3>
                <div class="log-box">
                    {% for t in emu.trace %}
                    <div>[{{ t.time }}] PC={{ t.PC }} | <code>{{ t.instruction }}</code> | {{ t.desc }}</div>
                    {% else %}
                    <div>No instructions stepped yet.</div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if tab == 'activity' %}
            <div class="panel">
                <h3>🤖 Agentic AI Observe → Plan → Validate → Act → Verify Timeline</h3>
                <div class="log-box" style="max-height:350px;">
                    {% for e in timeline %}
                    <div class="log-item" style="margin-bottom:8px; border-bottom:1px dashed #334155; padding-bottom:6px;">
                        <span style="color:#38bdf8;">[{{ e.time }}]</span> <b style="color:#f59e0b;">[{{ e.stage }}]</b>: {{ e.message }}
                    </div>
                    {% else %}
                    <div>No agent events recorded yet. Run agent loop from dashboard.</div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if tab == 'reports' %}
            <div class="panel">
                <h3>📑 Academic Project Specifications</h3>
                <ul>
                    <li><b>Domain:</b> MPMC (Microprocessors and Microcontrollers) + Agentic AI</li>
                    <li><b>Architecture:</b> Flask Backend + 8051 Microcontroller Emulator + Deterministic Safety Engine</li>
                    <li><b>Safety Rules:</b> Priority 1 (Critical) & Priority 2 (Essential) loads are strictly protected by policy guardrails.</li>
                </ul>
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    """
    return render_template_string(TEMPLATE, load=load, limit=sim_state["load_limit_w"], is_over=is_over, status=sim_state["status"], apps=sim_state["appliances"], tab=sim_state["tab"], timeline=sim_state["timeline"], emu=emu_state)

def run_agent_logic():
    log_agent("OBSERVE", f"Polled load: {total_load()}W (Limit: {sim_state['load_limit_w']}W).")
    if total_load() <= sim_state["load_limit_w"]:
        sim_state["status"] = "Normal"
        log_agent("VERIFY", "Demand within limit. No action needed.")
        return
    
    sim_state["status"] = "Overload Active"
    log_agent("PLAN", "Formulating plan to shed non-essential loads.")
    
    sheddable = [a for a in sim_state["appliances"] if a["is_on"] and a["priority"] > 2]
    if not sheddable:
        sim_state["status"] = "Guardrail Lockdown"
        log_agent("VALIDATE", "Blocked: Only Priority 1/2 protected loads active.")
        return
        
    target = sorted(sheddable, key=lambda x: (x["priority"], x["wattage"]), reverse=True)[0]
    log_agent("VALIDATE", f"Safety check passed for '{target['name']}' (Priority {target['priority']}).")
    
    target["is_on"] = False
    log_agent("ACT", f"Shedded appliance '{target['name']}' ({target['wattage']}W).")
    
    new_load = total_load()
    log_agent("VERIFY", f"New active load is {new_load}W.")
    
    if new_load <= sim_state["load_limit_w"]:
        sim_state["status"] = "Overload Resolved"
        log_agent("SUCCESS", "Overload resolved and verified successfully!")
    else:
        sim_state["status"] = "Partial Reduction"
        log_agent("INFO", "Load reduced but still above limit.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
