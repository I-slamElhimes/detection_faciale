# routes/presences.py
from flask import Blueprint, request, jsonify
from db_config import get_db
from bson.objectid import ObjectId
from datetime import datetime

presences_bp = Blueprint("presences", __name__)


# ──────────────────────────────────────────────────────────────────────────────
# GET /presences/<seance_id>
# ──────────────────────────────────────────────────────────────────────────────
@presences_bp.route("/presences/<seance_id>", methods=["GET"])
def get_presences(seance_id):
    try:
        db = get_db()
        presences = list(db["presences"].find({"seance_id": ObjectId(seance_id)}))
        result = []
        for p in presences:
            result.append({
                "id":            str(p["_id"]),
                "personne_id":   str(p["personne_id"]),
                "type":          p.get("type", "etudiant"),
                "statut":        p.get("statut", "present"),
                "heure_arrivee": p.get("heure_arrivee", ""),
                "justifie":      p.get("justifie", False),
                "motif":         p.get("motif", "")
            })
        return jsonify({"seance_id": seance_id, "presences": result, "total": len(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# POST /presences
# ──────────────────────────────────────────────────────────────────────────────
@presences_bp.route("/presences", methods=["POST"])
def post_presence():
    try:
        db   = get_db()
        data = request.json

        seance_id     = data.get("seance_id")
        personne_id   = data.get("personne_id")
        type_personne = data.get("type", "etudiant")
        statut        = data.get("statut", "present")

        if not seance_id or not personne_id:
            return jsonify({"error": "seance_id et personne_id sont requis"}), 400

        presence = {
            "seance_id":     ObjectId(seance_id),
            "personne_id":   ObjectId(personne_id),
            "type":          type_personne,
            "statut":        statut,
            "heure_arrivee": datetime.now().strftime("%H:%M"),
            "justifie":      False,
            "motif":         ""
        }

        db["presences"].update_one(
            {"seance_id": ObjectId(seance_id), "personne_id": ObjectId(personne_id)},
            {"$set": presence},
            upsert=True
        )
        return jsonify({"message": "✅ Présence enregistrée", "statut": statut})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# GET /rapport/<seance_id>
# Rapport complet d'une séance
# ──────────────────────────────────────────────────────────────────────────────
@presences_bp.route("/rapport/<seance_id>", methods=["GET"])
def get_rapport(seance_id):
    try:
        db     = get_db()
        seance = db["seances"].find_one({"_id": ObjectId(seance_id)})
        if not seance:
            return jsonify({"error": "Séance introuvable"}), 404

        groupe_id      = seance["groupe_id"]
        tous_etudiants = list(db["etudiants"].find({"groupe_id": groupe_id}))
        presences_docs = list(db["presences"].find({"seance_id": ObjectId(seance_id)}))

        ids_presents = {
            str(p["personne_id"])
            for p in presences_docs
            if p["statut"] == "present"
        }

        presents = []
        absents  = []
        for etu in tous_etudiants:
            info = {
                "id":     str(etu["_id"]),
                "nom":    etu["nom"],
                "prenom": etu["prenom"]
            }
            if str(etu["_id"]) in ids_presents:
                presents.append(info)
            else:
                absents.append(info)

        prof         = db["professeurs"].find_one({"_id": seance["prof_id"]})
        prof_present = str(seance["prof_id"]) in ids_presents
        salle        = db["salles"].find_one({"_id": seance.get("salle_id")})

        total = len(tous_etudiants)
        taux  = f"{(len(presents)/total*100):.1f}%" if total > 0 else "0%"

        return jsonify({
            "seance_id":   seance_id,
            "matiere":     seance.get("matiere", "N/A"),
            "date":        seance.get("date", ""),
            "heure_debut": seance.get("heure_debut", ""),
            "heure_fin":   seance.get("heure_fin", ""),
            "salle":       salle["num_salle"] if salle else "N/A",
            "professeur": {
                "id":      str(seance["prof_id"]),
                "nom":     prof["nom"]    if prof else "N/A",
                "prenom":  prof["prenom"] if prof else "",
                "present": prof_present
            },
            "stats": {
                "total":    total,
                "presents": len(presents),
                "absents":  len(absents),
                "taux":     taux
            },
            "details": {
                "presents": presents,
                "absents":  absents
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# GET /rapports
# Liste tous les rapports (toutes les séances avec stats de présence)
# Utilisé par le dashboard admin
# ──────────────────────────────────────────────────────────────────────────────
@presences_bp.route("/rapports", methods=["GET"])
def get_tous_rapports():
    try:
        db      = get_db()
        seances = list(db["seances"].find().sort("date", -1).limit(50))
        result  = []

        for seance in seances:
            groupe         = db["groupes"].find_one({"_id": seance.get("groupe_id")})
            prof           = db["professeurs"].find_one({"_id": seance.get("prof_id")})
            tous_etudiants = list(db["etudiants"].find({"groupe_id": seance.get("groupe_id")}))
            presences_docs = list(db["presences"].find({"seance_id": seance["_id"]}))

            ids_presents = {
                str(p["personne_id"])
                for p in presences_docs
                if p["statut"] == "present"
            }

            nb_presents = sum(1 for e in tous_etudiants if str(e["_id"]) in ids_presents)
            nb_absents  = len(tous_etudiants) - nb_presents
            total       = len(tous_etudiants)
            taux        = f"{(nb_presents/total*100):.1f}%" if total > 0 else "0%"

            prof_present = str(seance.get("prof_id", "")) in ids_presents

            result.append({
                "seance_id":    str(seance["_id"]),
                "matiere":      seance.get("matiere", "N/A"),
                "groupe":       groupe["nom"] if groupe else "?",
                "date":         seance.get("date", ""),
                "heure_debut":  seance.get("heure_debut", ""),
                "heure_fin":    seance.get("heure_fin", ""),
                "nb_presents":  nb_presents,
                "nb_absents":   nb_absents,
                "taux_presence": taux,
                "prof_present": prof_present,
                "genere_le":    str(seance.get("creee_le", ""))
            })

        return jsonify({"rapports": result, "total": len(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────────
# PUT /justifier/<presence_id>
# ──────────────────────────────────────────────────────────────────────────────
@presences_bp.route("/justifier/<presence_id>", methods=["PUT"])
def justifier(presence_id):
    try:
        db    = get_db()
        data  = request.json or {}
        motif = data.get("motif", "")
        db["presences"].update_one(
            {"_id": ObjectId(presence_id)},
            {"$set": {"justifie": True, "motif": motif}}
        )
        return jsonify({"message": "✅ Absence justifiée"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500