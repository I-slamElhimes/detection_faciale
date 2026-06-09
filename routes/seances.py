# routes/seances.py
# ─────────────────────────────────────────────────────────────────────────────
# Endpoints de gestion des séances (pour l'admin).
#
#   POST   /seances               → créer une séance
#   GET    /seances               → lister (filtre: ?groupe_id= &date= &salle_id=)
#   GET    /seances/<id>          → détail d'une séance
#   PUT    /seances/<id>          → modifier une séance
#   DELETE /seances/<id>          → supprimer une séance
#   GET    /seances/aujourd_hui   → toutes les séances du jour
# ─────────────────────────────────────────────────────────────────────────────

from flask import Blueprint, request, jsonify
from db_config import get_db
from bson.objectid import ObjectId
from datetime import datetime

seances_bp = Blueprint("seances", __name__)


def fmt_seance(s, db):
    """Formate un document séance pour la réponse JSON."""
    groupe = db["groupes"].find_one({"_id": s.get("groupe_id")})
    prof   = db["professeurs"].find_one({"_id": s.get("prof_id")})
    salle  = db["salles"].find_one({"_id": s.get("salle_id")})

    # ✅ FIX : le champ est stocké "status" dans camera.py mais le frontend
    # du dashboard utilise "statut" — on expose les deux pour compatibilité
    status_val = s.get("statut") or s.get("status") or "en_attente"

    return {
        "id":          str(s["_id"]),
        "groupe_id":   str(s["groupe_id"]),
        "groupe_nom":  groupe["nom"] if groupe else "?",
        "prof_id":     str(s["prof_id"]) if s.get("prof_id") else None,
        "prof_nom":    f"{prof['nom']} {prof['prenom']}" if prof else "?",
        "salle_id":    str(s["salle_id"]) if s.get("salle_id") else None,
        "salle_nom":   salle["num_salle"] if salle else "?",
        "matiere":     s.get("matiere", ""),
        "date":        s.get("date", ""),
        "heure_debut": s.get("heure_debut", ""),
        "heure_fin":   s.get("heure_fin", ""),
        # ✅ Les deux noms pour compatibilité (camera.py écrit "status",
        #    le dashboard lit "statut")
        "statut":      status_val,
        "status":      status_val,
        "creee_le":    str(s.get("creee_le", ""))
    }


# ══════════════════════════════════════════════════════════════════════════════
#  POST /seances — Créer une séance
# ══════════════════════════════════════════════════════════════════════════════
@seances_bp.route("/seances", methods=["POST"])
def creer_seance():
    try:
        db   = get_db()
        data = request.json or {}

        requis    = ["groupe_id", "prof_id", "salle_id", "matiere", "date", "heure_debut", "heure_fin"]
        manquants = [r for r in requis if not data.get(r)]
        if manquants:
            return jsonify({"error": f"Champs requis : {', '.join(manquants)}"}), 400

        groupe_id = ObjectId(data["groupe_id"])
        prof_id   = ObjectId(data["prof_id"])
        salle_id  = ObjectId(data["salle_id"])

        if not db["groupes"].find_one({"_id": groupe_id}):
            return jsonify({"error": "Groupe introuvable"}), 404
        if not db["professeurs"].find_one({"_id": prof_id}):
            return jsonify({"error": "Professeur introuvable"}), 404
        if not db["salles"].find_one({"_id": salle_id}):
            return jsonify({"error": "Salle introuvable"}), 404

        conflit = db["seances"].find_one({
            "salle_id": salle_id,
            "date":     data["date"],
            "$or": [{
                "heure_debut": {"$lt": data["heure_fin"]},
                "heure_fin":   {"$gt": data["heure_debut"]}
            }]
        })
        if conflit:
            return jsonify({
                "error": f"Conflit : séance existante dans cette salle "
                         f"de {conflit['heure_debut']} à {conflit['heure_fin']}"
            }), 409

        seance = {
            "groupe_id":   groupe_id,
            "prof_id":     prof_id,
            "salle_id":    salle_id,
            "matiere":     data["matiere"].strip(),
            "date":        data["date"],
            "heure_debut": data["heure_debut"],
            "heure_fin":   data["heure_fin"],
            # ✅ Les deux champs pour compatibilité totale
            "statut":      "en_attente",
            "status":      "en_attente",
            "creee_le":    datetime.now()
        }

        r = db["seances"].insert_one(seance)
        return jsonify({"message": "✅ Séance créée", "seance_id": str(r.inserted_id)}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  GET /seances — Lister les séances
# ══════════════════════════════════════════════════════════════════════════════
@seances_bp.route("/seances", methods=["GET"])
def lister_seances():
    try:
        db     = get_db()
        filtre = {}

        if request.args.get("groupe_id"):
            filtre["groupe_id"] = ObjectId(request.args["groupe_id"])
        if request.args.get("salle_id"):
            filtre["salle_id"] = ObjectId(request.args["salle_id"])
        if request.args.get("date"):
            filtre["date"] = request.args["date"]

        seances = [fmt_seance(s, db) for s in db["seances"].find(filtre).sort("heure_debut", 1)]
        return jsonify({"seances": seances, "total": len(seances)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  GET /seances/aujourd_hui
# ══════════════════════════════════════════════════════════════════════════════
@seances_bp.route("/seances/aujourd_hui", methods=["GET"])
def seances_du_jour():
    try:
        db    = get_db()
        today = datetime.now().strftime("%Y-%m-%d")
        docs  = db["seances"].find({"date": today}).sort("heure_debut", 1)
        return jsonify({
            "date":    today,
            "seances": [fmt_seance(s, db) for s in docs]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  GET /seances/<id>
# ══════════════════════════════════════════════════════════════════════════════
@seances_bp.route("/seances/<seance_id>", methods=["GET"])
def get_seance(seance_id):
    try:
        db     = get_db()
        seance = db["seances"].find_one({"_id": ObjectId(seance_id)})
        if not seance:
            return jsonify({"error": "Séance introuvable"}), 404
        return jsonify(fmt_seance(seance, db))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  PUT /seances/<id>
# ══════════════════════════════════════════════════════════════════════════════
@seances_bp.route("/seances/<seance_id>", methods=["PUT"])
def modifier_seance(seance_id):
    try:
        db     = get_db()
        seance = db["seances"].find_one({"_id": ObjectId(seance_id)})
        if not seance:
            return jsonify({"error": "Séance introuvable"}), 404

        status_actuel = seance.get("statut") or seance.get("status", "")
        if status_actuel == "en_cours":
            return jsonify({"error": "Impossible de modifier une séance en cours"}), 409

        data = request.json or {}
        maj  = {}

        if "matiere"     in data: maj["matiere"]     = data["matiere"].strip()
        if "date"        in data: maj["date"]        = data["date"]
        if "heure_debut" in data: maj["heure_debut"] = data["heure_debut"]
        if "heure_fin"   in data: maj["heure_fin"]   = data["heure_fin"]
        if "prof_id"     in data: maj["prof_id"]     = ObjectId(data["prof_id"])
        if "salle_id"    in data: maj["salle_id"]    = ObjectId(data["salle_id"])

        if not maj:
            return jsonify({"error": "Aucune donnée à modifier"}), 400

        db["seances"].update_one({"_id": ObjectId(seance_id)}, {"$set": maj})
        return jsonify({"message": "✅ Séance modifiée"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  DELETE /seances/<id>
# ══════════════════════════════════════════════════════════════════════════════
@seances_bp.route("/seances/<seance_id>", methods=["DELETE"])
def supprimer_seance(seance_id):
    try:
        db     = get_db()
        seance = db["seances"].find_one({"_id": ObjectId(seance_id)})
        if not seance:
            return jsonify({"error": "Séance introuvable"}), 404

        status_actuel = seance.get("statut") or seance.get("status", "")
        if status_actuel == "en_cours":
            return jsonify({"error": "Impossible de supprimer une séance en cours"}), 409

        db["seances"].delete_one({"_id": ObjectId(seance_id)})
        return jsonify({"message": "✅ Séance supprimée"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500