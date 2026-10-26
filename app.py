import os
import json
from flask import Flask, render_template_string, request
from datetime import datetime

app = Flask(__name__)

DEFAULT_APPLIANCES = [
    {"id": "1", "name": "Medical Oxygen Concentrator", "watt": 600, "on": True, "prio": 1},
    {"id": "2", "name": "Refrigerator", "watt": 400, "on": True, "prio": 2},
    {"id": "3", "name": "Smart Hub & Lights", "watt": 150, "on": True, "prio": 3},
    {"id": "4", "name": "Air Conditioner", "watt": 1500, "on": True, "prio": 4},
    {"id": "5", "name": "Water Heater", "watt": 1200, "on": True, "prio": 4}
]

state = {"appliances": json.loads(json.dumps(DEFAULT_APPLIANCES)), "limit": 2000, "logs": [], "status": "Normal"}

def log(stage, msg):
    state["logs"].insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "stage": stage, "msg": msg})

def get_total():
    return sum(a["watt"] for a in state["appliances"] if a["on"])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        act = request.form.get("action")
        if act == "reset":
            state["appliances"] = json.loads(json.dumps(DEFAULT_APPLIANCES))
            state["limit"] = 2000
            state["logs"] = []
            state["status"] = "Normal"
            log("RESET", "Reset to default settings.")
        elif act == "overload":
            state["limit"] = 1500
            for a in state["appliances"]:
                a["on"] = True
            state["status"] = "Severe Overload Triggered"
            log("SCENARIO", "All devices turned ON to test multi-appliance shedding.")
        elif act == "limit":
            try:
                state["limit"] = int(request.form.get("val", 2000))
                log("CONFIG", f"Load limit updated to {state['limit']}W.")
            except ValueError:
                pass
        elif act == "add":
            name = request.form.get("name", "").strip()
            try:
                watt = int(request.form.get("watt", 100))
                prio = int(request.form.get("prio", 3))
                if name:
                    state["appliances"].append({"id": str(len(state["appliances"])+1), "name": name, "watt": watt, "on": True, "prio": prio})
                    log("CONFIG", f"Added '{name}' ({watt}W, Priority {prio}).")
            except ValueError:
                pass
        elif act == "toggle":
            aid = request.form.get("aid")
            for a in state["appliances"]:
                if a["id"] == aid:
                    a["on"] = not a["on"]
                    log("USER", f"Toggled {a['name']}")
        elif act == "delete":
            aid = request.form.get("aid")
            state["appliances"] = [a for a in state["appliances"] if a["id"] != aid]
            log("CONFIG", "Deleted appliance.")
        elif act == "run":
            log("START", "Autonomous Multi-Shedding Agent Loop Started.")
            count = 0
            while get_total() > state["limit"] and count < 5:
                sheddable = [a for a in state["appliances"] if a["on"] and a["prio"] > 1]
                if not sheddable:
                    state["status"] = "Guardrail Locked"
                    log("VALIDATE", "Blocked: Only Priority 1 Critical loads remain active!")
                    break
                target = max(sheddable, key=lambda x: (x["prio"], x["watt"]))
                log("PLAN", f"Selected lowest-priority heavy load: {target['name']} ({target['watt']}W, P{target['prio']})")
                if target["prio"] == 1:
                    log("VALIDATE", "Safety Guardrail blocked P1 shutdown.")
                    break
                target["on"] = False
                count += 1
                log("ACT", f"Shedded appliance: {target['name']}")
                log("VERIFY", f"Current Load: {get_total()}W")
            
            if get_total() <= state["limit"]:
                state["status"] = "Resolved (Multi-Shed)"
                log("SUCCESS", f"Overload resolved after shedding {count} appliance(s).")
            else:
                state["status"] = "Critical Limit Reached"

    total = get_total()
    is_over = total > state["limit"]
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LoadShield Agent</title>
        <style>
            body { font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; }
            .box { max-width: 900px; margin: auto; background: #1e293b; padding: 25px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
            h1 { color: #38bdf8; text-align: center; margin-bottom: 5px; }
            .sub { text-align: center; color: #94a3b8; margin-bottom: 20px; font-size: 14px; }
            .metrics { display: flex; justify-content: space-around; background: #0f172a; padding: 15px; border-radius: 6px; margin-bottom: 20px; text-align: center; }
            table { width: 100%; border-collapse: collapse; background: #0f172a; border-radius: 6px; overflow: hidden; margin-bottom: 20px; }
            th, td { padding: 10px 14px; border-bottom: 1px solid #334155; text-align: left; }
            th { background: #111827; color: #38bdf8; }
            .btn { background: #3b82f6; color: white; border: none; padding: 10px 18px; border-radius: 5px; cursor: pointer; font-weight: bold; }
            .btn-reset { background: #64748b; }
            .btn-danger { background: #ef4444; padding: 5px 10px; font-size: 12px; }
            .btn-scen { background: #d97706; }
            .logs { background: #0f172a; padding: 12px; border-radius: 6px; max-height: 180px; overflow-y: auto; font-family: monospace; font-size: 12px; }
            input, select { padding: 6px 10px; background: #0f172a; border: 1px solid #475569; color: white; border-radius: 4px; }
            .panel { background: #0f172a; padding: 15px; border-radius: 6px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🛡️ LoadShield AI</h1>
            <div class="sub">Autonomous Multi-Appliance Shedding & MPMC Safety Validator</div>
            
            <div class="metrics">
                <div><h3>{{ total }} W</h3><p>Active Load</p></div>
                <div><h3>{{ limit }} W</h3><p>Load Limit</p></div>
                <div><h3 style="color: {{ '#ef4444' if is_over else '#22c55e' }};">{{ 'OVERLOAD' if is_over else 'NORMAL' }}</h3><p>State</p></div>
                <div><h3 style="color: #fbbf24; font-size: 15px; margin-top: 4px;">{{ status }}</h3><p>Agent Status</p></div>
            </div>

            <div style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
                <form method="POST"><input type="hidden" name="action" value="run"><button type="submit" class="btn">🚀 Run Multi-Shedding Agent</button></form>
                <form method="POST"><input type="hidden" name="action" value="overload"><button type="submit" class="btn btn-scen">⚡ Trigger Heavy Overload</button></form>
                <form method="POST"><input type="hidden" name="action" value="reset"><button type="submit" class="btn btn-reset">🔄 Reset</button></form>
            </div>

            <div class="panel">
                <form method="POST" style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
                    <input type="hidden" name="action" value="limit">
                    <label>Set Limit (W):</label>
                    <input type="number" name="val" value="{{ limit }}" style="width: 100px;" required>
                    <button type="submit" class="btn" style="padding: 6px 12px; font-size: 13px;">Update</button>
                </form>
                <form method="POST" style="display: flex; gap: 10px; align-items: center;">
                    <input type="hidden" name="action" value="add">
                    <input type="text" name="name" placeholder="Appliance Name" required style="flex:2;">
                    <input type="number" name="watt" placeholder="Wattage" required style="flex:1;">
                    <select name="prio" style="flex:1;">
                        <option value="1">P1 (Critical)</option>
                        <option value="2">P2 (Essential)</option>
                        <option value="3">P3 (Standard)</option>
                        <option value="4" selected>P4 (Comfort)</option>
                    </select>
                    <button type="submit" class="btn" style="padding: 6px 12px; font-size: 13px;">+ Add</button>
                </form>
            </div>

            <h3>Connected Appliances</h3>
            <table>
                <tr><th>Name</th><th>Wattage</th><th>Priority</th><th>Status</th><th>Toggle</th><th>Action</th></tr>
                {% for a in apps %}
                <tr>
                    <td><strong>{{ a.name }}</strong></td>
                    <td>{{ a.watt }} W</td>
                    <td>Priority {{ a.prio }}</td>
                    <td>{{ '🟢 ON' if a.on else '🔴 OFF' }}</td>
                    <td>
                        <form method="POST" style="margin:0;"><input type="hidden" name="action" value="toggle"><input type="hidden" name="aid" value="{{ a.id }}"><button type="submit" style="background:#334155;color:white;border:none;padding:5px 10px;cursor:pointer;border-radius:3px;">Toggle</button></form>
                    </td>
                    <td>
                        <form method="POST" style="margin:0;"><input type="hidden" name="action" value="delete"><input type="hidden" name="aid" value="{{ a.id }}"><button type="submit" class="btn btn-danger">Delete</button></form>
                    </td>
                </tr>
                {% endfor %}
            </table>

            <h3>Agent Event Logs (Observe → Plan → Validate → Act → Verify)</h3>
            <div class="logs">
                {% if not logs %}<p style="color: #64748b; text-align: center; margin: 10px 0;">No events recorded yet.</p>{% endif %}
                {% for l in logs %}
                <div style="margin-bottom: 6px; border-bottom: 1px dashed #334155; padding-bottom: 4px;">
                    <span style="color: #38bdf8;">[{{ l.time }}]</span> <b style="color: #fbbf24;">[{{ l.stage }}]</b>: {{ l.msg }}
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, total=total, limit=state["limit"], is_over=is_over, status=state["status"], apps=state["appliances"], logs=state["logs"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
