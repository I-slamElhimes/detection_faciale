# routes/auth.py
# ─────────────────────────────────────────────────────────────────────────────
#   POST /login        → vérifie identifiants, retourne rôle + redirect
#   GET  /logout       → déconnexion
# ─────────────────────────────────────────────────────────────────────────────

from flask import Blueprint, request, jsonify, session, redirect, url_for
from db_config import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Body JSON :
    {
      "username": "admin",
      "password": "admin123",
      "role":     "admin"   ← "admin" | "professeur" | "etudiant"
    }
    """
    try:
        db       = get_db()
        data     = request.json or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        role     = data.get("role", "admin")

        if not username or not password:
            return jsonify({"error": "Identifiants requis"}), 400

        # ── Admin ──────────────────────────────────────────────────────────
        if role == "admin":
            user = db["administrateurs"].find_one({
                "$or": [
                    {"username": username},
                    {"login":    username}
                ],
                "password": password
            })
            if user:
                return jsonify({
                    "success":  True,
                    "role":     "admin",
                    "nom":      user.get("nom", "Admin"),
                    "prenom":   user.get("prenom", ""),
                    "redirect": "/admin"
                })

        # ── Professeur ────────────────────────────────────────────────────
        elif role == "professeur":
            user = db["professeurs"].find_one({
                "$or": [
                    {"username": username},
                    {"email":    username},
                    {"cne":      username}
                ],
                "password": password
            })
            if user:
                return jsonify({
                    "success":   True,
                    "role":      "professeur",
                    "id":        str(user["_id"]),
                    "nom":       user.get("nom", ""),
                    "prenom":    user.get("prenom", ""),
                    "matiere":   user.get("matiere", ""),
                    "redirect":  "/prof"
                })

        # ── Étudiant ──────────────────────────────────────────────────────
        elif role == "etudiant":
            user = db["etudiants"].find_one({
                "$or": [
                    {"cne":      username},
                    {"email":    username},
                    {"username": username}
                ],
                "password": password
            })
            if user:
                groupe = db["groupes"].find_one({"_id": user.get("groupe_id")})
                return jsonify({
                    "success":    True,
                    "role":       "etudiant",
                    "id":         str(user["_id"]),
                    "nom":        user.get("nom", ""),
                    "prenom":     user.get("prenom", ""),
                    "cne":        user.get("cne", ""),
                    "groupe_id":  str(user.get("groupe_id", "")),
                    "groupe_nom": groupe["nom"] if groupe else "?",
                    "redirect":   "/etudiant"
                })

        return jsonify({"error": "Identifiants incorrects"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/logout", methods=["GET"])
def logout():
    return redirect("/login")