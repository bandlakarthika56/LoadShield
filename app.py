import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LoadShield: AI Load Management Simulator</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 50px; }
            .card { background: #1e293b; max-width: 600px; margin: auto; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
            h1 { color: #38bdf8; }
            p { color: #94a3b8; font-size: 16px; line-height: 1.5; }
            .status { background: #22c55e; color: white; padding: 8px 16px; border-radius: 20px; display: inline-block; font-weight: bold; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🛡️ LoadShield Simulator</h1>
            <p>Agentic AI Load Management & MPMC Safety Validator System is live and operational.</p>
            <p><strong>Architecture:</strong> Observe → Plan → Validate → Act → Verify</p>
            <div class="status">● System Online & Protected</div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
