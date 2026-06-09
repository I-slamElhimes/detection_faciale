# app.py
from flask import Flask, render_template
from flask_cors import CORS
from routes.identify  import identify_bp
from routes.presences import presences_bp
from routes.admin     import admin_bp
from routes.seances   import seances_bp
from routes.auth      import auth_bp        # ✅ NOUVEAU

app = Flask(__name__)
app.secret_key = "faceattend_secret_2026"   # pour les sessions
CORS(app)

app.register_blueprint(identify_bp)
app.register_blueprint(presences_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(seances_bp)
app.register_blueprint(auth_bp)             # ✅ NOUVEAU

# ── Pages HTML ───────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')
@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/admin")
def admin_panel():
    return render_template("admin.html")

@app.route("/prof")
def prof_panel():
    return render_template("prof.html")

@app.route("/etudiant")
def etudiant_panel():
    return render_template("etudiant.html")

if __name__ == "__main__":
    print("🚀 Serveur Flask démarré sur http://127.0.0.1:5000")
    print("\n🌐 Interfaces web :")
    print("   http://127.0.0.1:5000/login     ← Page de connexion")
    print("   http://127.0.0.1:5000/admin     ← Dashboard Admin")
    print("   http://127.0.0.1:5000/prof      ← Vue Professeur")
    print("   http://127.0.0.1:5000/etudiant  ← Vue Étudiant")
    print("\n📋 API Routes :")
    print("   POST   /login")
    print("   POST   /identifier")
    print("   POST   /presences")
    print("   GET    /presences/<seance_id>")
    print("   GET    /rapport/<seance_id>")
    print("   GET    /rapports")
    print("   PUT    /justifier/<presence_id>")
    print("   POST   /seances")
    print("   GET    /seances")
    print("   GET    /seances/aujourd_hui")
    print("   GET    /seances/<id>")
    print("   PUT    /seances/<id>")
    print("   DELETE /seances/<id>")
    print("   GET    /admin/filieres")
    print("   POST   /admin/filieres")
    print("   PUT    /admin/filieres/<id>")
    print("   DELETE /admin/filieres/<id>")
    print("   GET    /admin/groupes")
    print("   POST   /admin/groupes")
    print("   PUT    /admin/groupes/<id>")
    print("   DELETE /admin/groupes/<id>")
    print("   POST   /admin/groupes/<id>/emploi")
    print("   GET    /admin/etudiants")
    print("   POST   /admin/etudiants")
    print("   PUT    /admin/etudiants/<id>")
    print("   DELETE /admin/etudiants/<id>")
    print("   GET    /admin/professeurs")
    print("   POST   /admin/professeurs")
    print("   PUT    /admin/professeurs/<id>")
    print("   DELETE /admin/professeurs/<id>")
    app.run(debug=True, port=5000)