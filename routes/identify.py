# routes/identify.py
# ─────────────────────────────────────────────────────────────────────────────
# POST /identifier
# Reçoit un frame de camera.py, identifie la personne.
# Cherche SEULEMENT dans le groupe concerné + le prof de la séance.
# Le seuil_cosinus vient de la collection cameras (configurable par salle).
# ─────────────────────────────────────────────────────────────────────────────

from flask import Blueprint, request, jsonify
from deepface import DeepFace
from utils.cosinus import similarite_cosinus
from db_config import get_db
from bson.objectid import ObjectId
import os, uuid

identify_bp = Blueprint("identify", __name__)

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)


@identify_bp.route("/identifier", methods=["POST"])
def identifier():
    """
    Paramètres reçus (multipart/form-data) :
        image      — fichier image (frame de la caméra)
        groupe_id  — ID du groupe de la séance
        prof_id    — ID du prof de la séance
        salle_id   — ID de la salle (pour récupérer seuil_cosinus)

    Retourne :
        { identifie, id, nom, prenom, type, distance }
    """
    try:
        db = get_db()

        # ── Paramètres ────────────────────────────────────────────────────
        groupe_id = request.form.get("groupe_id")
        prof_id   = request.form.get("prof_id")
        salle_id  = request.form.get("salle_id")

        # Récupérer le seuil depuis la caméra de cette salle
        # (configurable dans MongoDB — défaut plan : 0.40)
        seuil = 0.40
        if salle_id:
            cam = db["cameras"].find_one({"salle_id": ObjectId(salle_id)})
            if cam:
                seuil = cam.get("seuil_cosinus", 0.40)

        # ── Image ─────────────────────────────────────────────────────────
        if "image" not in request.files:
            return jsonify({"error": "Champ 'image' requis"}), 400

        img_file = request.files["image"]
        img_path = os.path.join(TEMP_FOLDER, f"{uuid.uuid4()}.jpg")
        img_file.save(img_path)

        # ── Embedding ArcFace du frame ────────────────────────────────────
        result = DeepFace.represent(
            img_path=img_path,
            model_name="ArcFace",
            enforce_detection=False
        )
        embedding_recu = result[0]["embedding"]
        os.remove(img_path)

        meilleur       = None
        meilleure_dist = float("inf")
        type_personne  = None

        # ── Chercher dans le groupe concerné SEULEMENT ────────────────────
        filtre_etu = {"embedding": {"$ne": None}}
        if groupe_id:
            filtre_etu["groupe_id"] = ObjectId(groupe_id)

        for etu in db["etudiants"].find(filtre_etu):
            dist = similarite_cosinus(embedding_recu, etu["embedding"])
            if dist < meilleure_dist:
                meilleure_dist = dist
                meilleur       = etu
                type_personne  = "etudiant"

        # ── Chercher le prof de la séance SEULEMENT ───────────────────────
        filtre_prof = {"embedding": {"$ne": None}}
        if prof_id:
            filtre_prof["_id"] = ObjectId(prof_id)

        for prof in db["professeurs"].find(filtre_prof):
            dist = similarite_cosinus(embedding_recu, prof["embedding"])
            if dist < meilleure_dist:
                meilleure_dist = dist
                meilleur       = prof
                type_personne  = "professeur"

        # ── Résultat ──────────────────────────────────────────────────────
        if meilleur and meilleure_dist < seuil:
            return jsonify({
                "identifie": True,
                "id":        str(meilleur["_id"]),
                "nom":       meilleur["nom"],
                "prenom":    meilleur["prenom"],
                "type":      type_personne,
                "distance":  round(meilleure_dist, 4)
            })
        else:
            return jsonify({
                "identifie": False,
                "message":   "Personne non reconnue",
                "distance":  round(meilleure_dist, 4)
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500