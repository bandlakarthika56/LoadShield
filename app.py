import os
import json
from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)

DEFAULT_APPLIANCES = [
    {"id": "1", "name": "Medical Oxygen Concentrator", "watt": 600, "on": True, "prio": 1},
    {"id": "2", "name": "Refrigerator", "watt": 400, "on": True, "prio": 2},
    {"id": "3", "name": "Smart Hub & Lights", "watt": 150, "on": True, "prio": 3},
    {"id": "4", "name": "Air Conditioner", "watt": 1500, "on": True, "prio": 4},
    {"id": "5", "name": "Water Heater", "watt": 1200, "on": True, "prio": 4}
]

state = {"appliances": json.loads(json.dumps(DEFAULT_APPLIANCES)), "limit": 2500, "logs": [], "status": "Normal"}

def log(stage, msg):
    state["logs"].insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "stage": stage, "msg": msg})

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        act = request.form.get("action")
        if act == "reset":
            state["appliances"] = json.loads(json.dumps(DEFAULT_APPLIANCES))
            state["limit"] = 2500
            state["logs"] = []
            state["status"] = "Normal"
            log("RESET", "Reset to default parameters.")
        elif act == "toggle":
            aid = request.form.get("aid")
            for a in state["appliances"]:
                if a["id"] == aid:
                    a["on"] = not a["on"]
                    log("USER", f"Toggled {a['name']}")
        elif act == "run":
            total = sum(a["watt"] for a in state["appliances"] if a["on"])
            log("OBSERVE", f"Total load is {total}W (Limit: {state['limit']}W)")
            if total <= state["limit"]:
                state["status"] = "Normal"
                log("VERIFY", "Load within safe threshold.")
            else:
                sheddable = [a for a in state["appliances"] if a["on"] and a["prio"] > 1]
                if not sheddable:
                    state["status"] = "Guardrail Locked"
                    log("VALIDATE", "Blocked: Only Priority 1 critical loads active!")
                else:
                    target = max(sheddable, key=lambda x: (x["prio"], x["watt"]))
                    target["on"] = False
                    state["status"] = "Overload Resolved"
                    log("ACT", f"Shedded non-essential load: {target['name']} ({target['watt']}W)")

    total = sum(a["watt"] for a in state["appliances"] if a["on"])
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LoadShield AI</title>
        <style>
            body {{ font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; }}
            .box {{ max-width: 800px; margin: auto; background: #1e293b; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
            h1 {{ color: #38bdf8; text-align: center; }}
            .metrics {{ display: flex; justify-content: space-around; background: #0f172a; padding: 15px; border-radius: 6px; margin-bottom: 20px; text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; background: #0f172a; border-radius: 6px; overflow: hidden; margin-bottom: 20px; }}
            th, td {{ padding: 10px 15px; border-bottom: 1px solid #334155; text-align: left; }}
            th {{ background: #111827; color: #38bdf8; }}
            .btn {{ background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }}
            .btn-reset {{ background: #64748b; }}
            .logs {{ background: #0f172a; padding: 10px; border-radius: 6px; max-height: 180px; overflow-y: auto; font-family: monospace; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🛡️ LoadShield AI Simulator</h1>
            <div class="metrics">
                <div><h3>{total} W</h3><p>Active Load</p></div>
                <div><h3>{state['limit']} W</h3><p>Limit</p></div>
                <div><h3 style="color: {'#ef4444' if total > state['limit'] else '#22c55e'};">{'OVERLOAD' if total > state['limit'] else 'NORMAL'}</h3><p>State</p></div>
                <div><h3 style="color: #fbbf24; font-size: 16px; margin-top: 5px;">{state['status']}</h3><p>Agent Status</p></div>
            </div>
            <form method="POST" style="display: flex; gap: 10px; margin-bottom: 20px;">
                <input type="hidden" name="action" value="run"><button type="submit" class="btn">🚀 Run Agent Loop</button>
            </form>
            <form method="POST" style="margin-bottom: 20px;">
                <input type="hidden" name="action" value="reset"><button type="submit" class="btn btn-reset">🔄 Reset Defaults</button>
            </form>
            <h3>Appliances & Priorities</h3>
            <table>
                <tr><th>Name</th><th>Wattage</th><th>Priority</th><th>Status</th><th>Toggle</th></tr>
                {''.join(f"<tr><td>{a['name']}</td><td>{a['watt']}W</td><td>Priority {a['prio']}</td><td>{'🟢 ON' if a['on'] else '🔴 OFF'}</td><td><form method='POST'><input type='hidden' name='action' value='toggle'><input type='hidden' name='aid' value='{a['id']}'><button type='submit' style='background:#334155;color:white;border:none;padding:5px 10px;cursor:pointer;'>Toggle</button></form></td></tr>" for a in state['appliances'])}
            </table>
            <h3>Agent Event Logs (Observe → Plan → Validate → Act → Verify)</h3>
            <div class="logs">
                {''.join(f"<div>[{l['time']}] <b>[{l['stage']}]</b>: {l['msg']}</div>" for l in state['logs']) or 'No events yet.'}
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
