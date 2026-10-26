import os
import json
from flask import Flask, render_template_string, request
from datetime import datetime

app = Flask(__name__)

DEFAULT_APPLIANCES = [
    {"appliance_id": "app_1", "name": "Medical Oxygen Concentrator", "wattage": 600, "is_on": True, "is_essential": True},
    {"appliance_id": "app_2", "name": "Refrigerator", "wattage": 400, "is_on": True, "is_essential": True},
    {"appliance_id": "app_3", "name": "Air Conditioner", "wattage": 1500, "is_on": True, "is_essential": False},
    {"appliance_id": "app_4", "name": "Electric Water Heater", "wattage": 1200, "is_on": True, "is_essential": False},
    {"appliance_id": "app_5", "name": "Gaming PC & Monitor", "wattage": 500, "is_on": False, "is_essential": False}
]
DEFAULT_LOAD_LIMIT = 2500

sim_state = {
    "appliances": json.loads(json.dumps(DEFAULT_APPLIANCES)),
    "load_limit_w": DEFAULT_LOAD_LIMIT,
    "event_log": [],
    "run_status": "Normal"
}

def log_event(stage: str, message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    sim_state["event_log"].insert(0, {"timestamp": timestamp, "stage": stage, "message": message})

def recalculate_load():
    return sum(app["wattage"] for app in sim_state["appliances"] if app["is_on"])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "reset":
            sim_state["appliances"] = json.loads(json.dumps(DEFAULT_APPLIANCES))
            sim_state["load_limit_w"] = DEFAULT_LOAD_LIMIT
            sim_state["event_log"] = []
            sim_state["run_status"] = "Normal"
            log_event("RESET", "Simulation state returned to default test parameters.")
        elif action == "update_limit":
            try:
                new_limit = int(request.form.get("load_limit", 2500))
                sim_state["load_limit_w"] = new_limit
                log_event("CONFIG", f"Household load limit updated to {new_limit}W.")
            except ValueError:
                pass
        elif action == "add_appliance":
            name = request.form.get("name", "").strip()
            try:
                wattage = int(request.form.get("wattage", 100))
                is_essential = True if request.form.get("is_essential") == "on" else False
                if name:
                    new_id = f"app_{len(sim_state['appliances']) + 1}"
                    sim_state["appliances"].append({
                        "appliance_id": new_id,
                        "name": name,
                        "wattage": wattage,
                        "is_on": True,
                        "is_essential": is_essential
                    })
                    log_event("CONFIG", f"Added custom appliance: '{name}' ({wattage}W, Essential: {is_essential}).")
            except ValueError:
                pass
        elif action == "run_agent":
            run_agent_logic()
        elif action == "toggle":
            app_id = request.form.get("app_id")
            for app in sim_state["appliances"]:
                if app["appliance_id"] == app_id:
                    app["is_on"] = not app["is_on"]
                    log_event("USER", f"Toggled '{app['name']}' to {'ON' if app['is_on'] else 'OFF'}.")
        elif action == "delete":
            app_id = request.form.get("app_id")
            sim_state["appliances"] = [app for app in sim_state["appliances"] if app["appliance_id"] != app_id]
            log_event("CONFIG", "Removed appliance from network profile.")
            
    total_load = recalculate_load()
    is_overloaded = total_load > sim_state["load_limit_w"]
    
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LoadShield: Advanced AI Load Manager</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
            .container { max-width: 1000px; margin: auto; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 4px 25px rgba(0,0,0,0.6); }
            h1 { color: #38bdf8; text-align: center; margin-bottom: 5px; }
            .subtitle { text-align: center; color: #94a3b8; margin-top: 0; margin-bottom: 25px; }
            .metrics { display: flex; justify-content: space-around; background: #0f172a; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; flex-wrap: wrap; gap: 10px; }
            .metric-box h3 { margin: 0; font-size: 24px; color: #38bdf8; }
            .metric-box p { margin: 5px 0 0; color: #94a3b8; font-size: 14px; }
            .panel { background: #0f172a; padding: 20px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #334155; }
            .panel h3 { margin-top: 0; color: #38bdf8; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 20px; background: #0f172a; border-radius: 8px; overflow: hidden; }
            th, td { padding: 12px 16px; border-bottom: 1px solid #334155; text-align: left; }
            th { background: #111827; color: #38bdf8; font-weight: 600; }
            .badge-on { background: #22c55e; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
            .badge-off { background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
            .btn { background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: bold; }
            .btn:hover { background: #2563eb; }
            .btn-reset { background: #64748b; }
            .btn-reset:hover { background: #475569; }
            .btn-danger { background: #ef4444; padding: 6px 10px; font-size: 12px; }
            .btn-danger:hover { background: #dc2626; }
            .logs { background: #0f172a; padding: 15px; border-radius: 8px; max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 13px; border: 1px solid #334155; }
            .log-item { margin-bottom: 8px; border-bottom: 1px dashed #334155; padding-bottom: 6px; }
            .form-grid { display: grid; grid-template-columns: 2fr 1fr 1fr auto; gap: 10px; align-items: center; }
            input[type="text"], input[type="number"] { padding: 8px 12px; background: #1e293b; border: 1px solid #475569; color: white; border-radius: 4px; width: 100%; box-sizing: border-box; }
            label { font-size: 14px; color: #cbd5e1; cursor: pointer; }
            .actions-bar { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ LoadShield Advanced</h1>
            <div class="subtitle">Agentic AI Load Management & MPMC Deterministic Safety Validator</div>
            
            <div class="metrics">
                <div class="metric-box">
                    <h3>{{ total_load }} W</h3>
                    <p>Active Load</p>
                </div>
                <div class="metric-box">
                    <h3>{{ load_limit }} W</h3>
                    <p>Load Limit</p>
                </div>
                <div class="metric-box">
                    <h3 style="color: {% if is_overloaded %}#ef4444{% else %}#22c55e{% endif %};">
                        {% if is_overloaded %}OVERLOADED{% else %}NORMAL{% endif %}
                    </h3>
                    <p>System State</p>
                </div>
                <div class="metric-box">
                    <h3 style="font-size: 15px; margin-top: 4px; color: #fbbf24;">{{ status }}</h3>
                    <p>Agent Status</p>
                </div>
            </div>

            <div class="actions-bar">
                <form method="POST">
                    <input type="hidden" name="action" value="run_agent">
                    <button type="submit" class="btn">🚀 Run Autonomous Agent Loop</button>
                </form>
                <form method="POST">
                    <input type="hidden" name="action" value="reset">
                    <button type="submit" class="btn btn-reset">🔄 Reset All Defaults</button>
                </form>
            </div>

            <!-- Configuration & Customization Panel -->
            <div class="panel">
                <h3>⚙️ Simulation & Guardrail Customization</h3>
                <form method="POST" style="margin-bottom: 15px; display: flex; gap: 10px; align-items: center;">
                    <input type="hidden" name="action" value="update_limit">
                    <label style="font-weight: bold;">Set Load Limit (W):</label>
                    <input type="number" name="load_limit" value="{{ load_limit }}" style="max-width: 150px;" required>
                    <button type="submit" class="btn" style="padding: 8px 15px; font-size: 14px;">Update Limit</button>
                </form>

                <form method="POST" class="form-grid">
                    <input type="hidden" name="action" value="add_appliance">
                    <input type="text" name="name" placeholder="Appliance Name (e.g. EV Charger)" required>
                    <input type="number" name="wattage" placeholder="Wattage (W)" required>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <input type="checkbox" name="is_essential" id="essential_chk">
                        <label for="essential_chk">Essential?</label>
                    </div>
                    <button type="submit" class="btn" style="padding: 8px 15px; font-size: 14px;">+ Add Device</button>
                </form>
            </div>

            <h3>Connected Appliances & Safety Policies</h3>
            <table>
                <tr>
                    <th>Appliance Name</th>
                    <th>Wattage</th>
                    <th>Safety Guardrail Policy</th>
                    <th>Status</th>
                    <th>Manual Control</th>
                    <th>Action</th>
                </tr>
                {% for app in appliances %}
                <tr>
                    <td><strong>{{ app.name }}</strong></td>
                    <td>{{ app.wattage }} W</td>
                    <td>{% if app.is_essential %}🔒 Essential (Protected by MPMC){% else %}⚡ Non-Essential (Sheddable){% endif %}</td>
                    <td>
                        {% if app.is_on %}<span class="badge-on">ON</span>{% else %}<span class="badge-off">OFF</span>{% endif %}
                    </td>
                    <td>
                        <form method="POST" style="margin:0;">
                            <input type="hidden" name="action" value="toggle">
                            <input type="hidden" name="app_id" value="{{ app.appliance_id }}">
                            <button type="submit" style="background:#334155; border:none; color:white; padding:6px 12px; border-radius:4px; cursor:pointer;">Toggle</button>
                        </form>
                    </td>
                    <td>
                        <form method="POST" style="margin:0;">
                            <input type="hidden" name="action" value="delete">
                            <input type="hidden" name="app_id" value="{{ app.appliance_id }}">
                            <button type="submit" class="btn btn-danger">Delete</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>

            <h3>Agent Event Log (Observe → Plan → Validate → Act → Verify)</h3>
            <div class="logs">
                {% if not logs %}
                <p style="color: #64748b; text-align: center; margin: 15px 0;">No events recorded yet. Run agent or modify loads to test conditions.</p>
                {% endif %}
                {% for log in logs %}
                <div class="log-item">
                    <span style="color: #38bdf8;">[{{ log.timestamp }}]</span> 
                    <strong style="color: #fbbf24;">[{{ log.stage }}]</strong>: 
                    {{ log.message }}
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(HTML_TEMPLATE, 
                                  total_load=total_load, 
                                  load_limit=sim_state["load_limit_w"], 
                                  is_overloaded=is_overloaded, 
                                  status=sim_state["run_status"],
                                  appliances=sim_state["appliances"],
                                  logs=sim_state["event_log"])

def run_agent_logic():
    log_event("START", "Agent loop initiated: Observe -> Plan -> Validate -> Act -> Verify.")
    total_load = recalculate_load()
    if total_load <= sim_state["load_limit_w"]:
        sim_state["run_status"] = "Normal"
        log_event("VERIFY", "Total load within safety threshold. No load shedding required.")
        return

    non_essential_on = [a for a in sim_state["appliances"] if a["is_on"] and not a["is_essential"]]
    if not non_essential_on:
        sim_state["run_status"] = "Blocked (Protected Loads)"
        log_event("VALIDATE", "Safety Guardrail: Only essential life-support loads remain active. Shutdown prevented.")
        return

    target = sorted(non_essential_on, key=lambda x: x["wattage"], reverse=True)[0]
    log_event("PLAN", f"Agent proposed shedding highest wattage non-essential load: '{target['name']}' ({target['wattage']}W).")

    if target["is_essential"]:
        sim_state["run_status"] = "Policy Violation Blocked"
        log_event("VALIDATE (REJECTED)", f"Deterministic Validator blocked unauthorized shutdown of essential load.")
        return

    target["is_on"] = False
    log_event("ACT", f"Successfully executed shutdown command for '{target['name']}'.")

    new_load = recalculate_load()
    if new_load <= sim_state["load_limit_w"]:
        sim_state["run_status"] = "Resolved"
        log_event("VERIFY", f"Overload successfully resolved! New active load: {new_load}W.")
    else:
        sim_state["run_status"] = "Partial Reduction"
        log_event("VERIFY", f"Load reduced to {new_load}W. Further evaluation queued for next agent cycle.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
