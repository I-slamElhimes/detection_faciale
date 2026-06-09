# routes/admin.py
# ─────────────────────────────────────────────────────────────────────────────
# Tous les endpoints de gestion pour l'administrateur :
#   - Filières       : CRUD
#   - Groupes        : CRUD + upload emploi du temps
#   - Étudiants      : CRUD + embedding ArcFace
#   - Professeurs    : CRUD + embedding ArcFace
#   - Justifications : liste + traitement (accepter / refuser)
#   - Séances        : génération automatique du jour
#   - Archives       : archivage + consultation
# ─────────────────────────────────────────────────────────────────────────────

from flask import Blueprint, request, jsonify, Response
from db_config import get_db
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from utils.embedding import extraire_embedding
import base64, tempfile, os

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt(doc):
    """Convertit ObjectId en str pour la réponse JSON."""
    doc["id"] = str(doc.pop("_id"))
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc


def photo_vers_base64_et_embedding(fichier):
    """
    Reçoit un FileStorage Flask (photo uploadée par l'admin).
    1. Lit les bytes
    2. Convertit en base64
    3. Écrit dans un fichier temporaire
    4. Calcule l'embedding ArcFace 512D
    5. Supprime le fichier temporaire
    Retourne (photo_b64: str, embedding: list[float])
    """
    img_bytes = fichier.read()
    photo_b64 = base64.b64encode(img_bytes).decode("utf-8")

    suffix = os.path.splitext(fichier.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name

    try:
        embedding = extraire_embedding(tmp_path)
    finally:
        os.remove(tmp_path)

    return photo_b64, embedding


# ══════════════════════════════════════════════════════════════════════════════
#  FILIÈRES
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/filieres", methods=["GET"])
def get_filieres():
    db = get_db()
    filieres = [fmt(f) for f in db["filieres"].find()]
    return jsonify({"filieres": filieres, "total": len(filieres)})


@admin_bp.route("/filieres", methods=["POST"])
def add_filiere():
    db   = get_db()
    data = request.json or {}
    nom  = data.get("nom", "").strip()

    if not nom:
        return jsonify({"error": "Le champ 'nom' est requis"}), 400
    if db["filieres"].find_one({"nom": nom}):
        return jsonify({"error": f"La filière '{nom}' existe déjà"}), 409

    r = db["filieres"].insert_one({
        "nom":         nom,
        "description": data.get("description", ""),
        "creee_le":    datetime.now()
    })
    return jsonify({"message": "✅ Filière ajoutée", "id": str(r.inserted_id)}), 201


@admin_bp.route("/filieres/<filiere_id>", methods=["PUT"])
def update_filiere(filiere_id):
    db   = get_db()
    data = request.json or {}
    maj  = {}
    if "nom"         in data: maj["nom"]         = data["nom"].strip()
    if "description" in data: maj["description"] = data["description"]
    if not maj:
        return jsonify({"error": "Aucune donnée à modifier"}), 400
    db["filieres"].update_one({"_id": ObjectId(filiere_id)}, {"$set": maj})
    return jsonify({"message": "✅ Filière modifiée"})


@admin_bp.route("/filieres/<filiere_id>", methods=["DELETE"])
def delete_filiere(filiere_id):
    db  = get_db()
    fid = ObjectId(filiere_id)
    nb  = db["groupes"].count_documents({"filiere_id": fid})
    if nb > 0:
        return jsonify({"error": f"Impossible : {nb} groupe(s) utilisent cette filière"}), 409
    db["filieres"].delete_one({"_id": fid})
    return jsonify({"message": "✅ Filière supprimée"})


# ══════════════════════════════════════════════════════════════════════════════
#  GROUPES
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/groupes", methods=["GET"])
def get_groupes():
    db         = get_db()
    filiere_id = request.args.get("filiere_id")
    filtre     = {"filiere_id": ObjectId(filiere_id)} if filiere_id else {}
    groupes    = []
    for g in db["groupes"].find(filtre):
        filiere = db["filieres"].find_one({"_id": g["filiere_id"]})
        nb_etu  = db["etudiants"].count_documents({"groupe_id": g["_id"]})
        groupes.append({
            "id":           str(g["_id"]),
            "nom":          g["nom"],
            "filiere_id":   str(g["filiere_id"]),
            "filiere_nom":  filiere["nom"] if filiere else "?",
            "nb_etudiants": nb_etu,
            # ✅ FIX : était "has_emploi", le frontend attend "a_emploi"
            "a_emploi":     g.get("emploi_du_temps") is not None
        })
    return jsonify({"groupes": groupes, "total": len(groupes)})


@admin_bp.route("/groupes", methods=["POST"])
def add_groupe():
    """
    ✅ FIX : accepte multipart/form-data (avec PDF optionnel)
    Champs : nom, filiere_id, emploi_du_temps (fichier PDF optionnel)
    """
    db = get_db()

    # Support multipart ET JSON
    if request.content_type and "multipart" in request.content_type:
        nom        = (request.form.get("nom")        or "").strip()
        filiere_id = (request.form.get("filiere_id") or "").strip()
    else:
        data       = request.json or {}
        nom        = data.get("nom", "").strip()
        filiere_id = data.get("filiere_id", "").strip()

    if not nom or not filiere_id:
        return jsonify({"error": "'nom' et 'filiere_id' sont requis"}), 400
    if not db["filieres"].find_one({"_id": ObjectId(filiere_id)}):
        return jsonify({"error": "Filière introuvable"}), 404

    doc = {
        "nom":             nom,
        "filiere_id":      ObjectId(filiere_id),
        "emploi_du_temps": None,
        "creee_le":        datetime.now()
    }

    # ✅ PDF optionnel dans la même requête
    # Accepte les noms de champ "emploi_du_temps" ET "pdf" (compatibilité)
    pdf_file = (
        request.files.get("emploi_du_temps") or
        request.files.get("pdf")
    )
    if pdf_file and pdf_file.filename:
        doc["emploi_du_temps"]    = base64.b64encode(pdf_file.read()).decode("utf-8")
        doc["emploi_nom_fichier"] = pdf_file.filename
        doc["emploi_uploade_le"]  = datetime.now()

    r = db["groupes"].insert_one(doc)
    return jsonify({"message": "✅ Groupe ajouté", "id": str(r.inserted_id)}), 201


@admin_bp.route("/groupes/<groupe_id>", methods=["PUT"])
def update_groupe(groupe_id):
    """
    ✅ FIX : accepte multipart (avec PDF optionnel) ET JSON
    """
    db  = get_db()
    maj = {}

    if request.content_type and "multipart" in request.content_type:
        if request.form.get("nom"):        maj["nom"]        = request.form["nom"].strip()
        if request.form.get("filiere_id"): maj["filiere_id"] = ObjectId(request.form["filiere_id"])

        pdf_file = (
            request.files.get("emploi_du_temps") or
            request.files.get("pdf")
        )
        if pdf_file and pdf_file.filename:
            maj["emploi_du_temps"]    = base64.b64encode(pdf_file.read()).decode("utf-8")
            maj["emploi_nom_fichier"] = pdf_file.filename
            maj["emploi_uploade_le"]  = datetime.now()
    else:
        data = request.json or {}
        if "nom"        in data: maj["nom"]        = data["nom"].strip()
        if "filiere_id" in data: maj["filiere_id"] = ObjectId(data["filiere_id"])

    if not maj:
        return jsonify({"error": "Aucune donnée à modifier"}), 400

    db["groupes"].update_one({"_id": ObjectId(groupe_id)}, {"$set": maj})
    return jsonify({"message": "✅ Groupe modifié"})


@admin_bp.route("/groupes/<groupe_id>", methods=["DELETE"])
def delete_groupe(groupe_id):
    db  = get_db()
    gid = ObjectId(groupe_id)
    nb  = db["etudiants"].count_documents({"groupe_id": gid})
    if nb > 0:
        return jsonify({"error": f"Impossible : {nb} étudiant(s) dans ce groupe"}), 409
    db["groupes"].delete_one({"_id": gid})
    return jsonify({"message": "✅ Groupe supprimé"})


@admin_bp.route("/groupes/<groupe_id>/emploi", methods=["POST"])
def upload_emploi(groupe_id):
    """Multipart : champ 'pdf' ou 'emploi_du_temps' = fichier PDF."""
    db = get_db()
    pdf_file = request.files.get("pdf") or request.files.get("emploi_du_temps")
    if not pdf_file:
        return jsonify({"error": "Champ 'pdf' requis"}), 400
    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Fichier PDF requis"}), 400

    contenu_b64 = base64.b64encode(pdf_file.read()).decode("utf-8")
    db["groupes"].update_one(
        {"_id": ObjectId(groupe_id)},
        {"$set": {
            "emploi_du_temps":    contenu_b64,
            "emploi_nom_fichier": pdf_file.filename,
            "emploi_uploade_le":  datetime.now()
        }}
    )
    return jsonify({"message": "✅ Emploi du temps enregistré"})


@admin_bp.route("/groupes/<groupe_id>/emploi", methods=["GET"])
def get_emploi(groupe_id):
    db     = get_db()
    groupe = db["groupes"].find_one({"_id": ObjectId(groupe_id)})
    if not groupe:
        return jsonify({"error": "Groupe introuvable"}), 404
    if not groupe.get("emploi_du_temps"):
        return jsonify({"error": "Aucun emploi du temps pour ce groupe"}), 404
    return jsonify({
        "groupe_id":   groupe_id,
        "nom_fichier": groupe.get("emploi_nom_fichier", "emploi.pdf"),
        "pdf_base64":  groupe["emploi_du_temps"],
        "uploade_le":  str(groupe.get("emploi_uploade_le", ""))
    })


# ══════════════════════════════════════════════════════════════════════════════
#  ÉTUDIANTS
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/etudiants", methods=["GET"])
def get_etudiants():
    db        = get_db()
    groupe_id = request.args.get("groupe_id")
    filtre    = {"groupe_id": ObjectId(groupe_id)} if groupe_id else {}
    result    = []
    for e in db["etudiants"].find(filtre):
        groupe  = db["groupes"].find_one({"_id": e.get("groupe_id")})
        # ✅ FIX : ajout filiere_nom manquant (affiché dans le tableau)
        filiere = db["filieres"].find_one({"_id": groupe["filiere_id"]}) if groupe else None
        eid = str(e["_id"])
        result.append({
            "id":          eid,
            "nom":         e["nom"],
            "prenom":      e["prenom"],
            "cne":         e.get("cne", ""),
            "groupe_id":   str(e.get("groupe_id", "")),
            "groupe_nom":  groupe["nom"]   if groupe  else "?",
            "filiere_nom": filiere["nom"]  if filiere else "?",
            "a_embedding": e.get("embedding") is not None,
            "a_photo":     e.get("photo_base64") is not None,
            # ✅ FIX PHOTOS : route qui sert la photo depuis MongoDB base64
            "photo_url":   f"/admin/photos/etudiant/{eid}" if e.get("photo_base64") else None
        })
    return jsonify({"etudiants": result, "total": len(result)})


@admin_bp.route("/etudiants", methods=["POST"])
def add_etudiant():
    db = get_db()

    nom       = (request.form.get("nom")       or "").strip()
    prenom    = (request.form.get("prenom")    or "").strip()
    cne       = (request.form.get("cne")       or "").strip()
    groupe_id = (request.form.get("groupe_id") or "").strip()

    if not nom or not prenom or not groupe_id:
        return jsonify({"error": "'nom', 'prenom', 'groupe_id' sont requis"}), 400
    if not db["groupes"].find_one({"_id": ObjectId(groupe_id)}):
        return jsonify({"error": "Groupe introuvable"}), 404

    photo_b64 = None
    embedding = None

    if "photo" in request.files and request.files["photo"].filename:
        try:
            photo_b64, embedding = photo_vers_base64_et_embedding(request.files["photo"])
        except Exception as e:
            return jsonify({"error": f"Erreur traitement photo : {str(e)}"}), 500

    r = db["etudiants"].insert_one({
        "nom":          nom,
        "prenom":       prenom,
        "cne":          cne,
        "groupe_id":    ObjectId(groupe_id),
        "photo_base64": photo_b64,
        "embedding":    embedding,
        "creee_le":     datetime.now()
    })

    msg = "✅ Étudiant ajouté avec embedding" if embedding else "✅ Étudiant ajouté (sans photo)"
    return jsonify({"message": msg, "id": str(r.inserted_id)}), 201


@admin_bp.route("/etudiants/<etudiant_id>", methods=["PUT"])
def update_etudiant(etudiant_id):
    db  = get_db()
    maj = {}

    if request.content_type and "multipart" in request.content_type:
        if request.form.get("nom"):    maj["nom"]    = request.form["nom"].strip()
        if request.form.get("prenom"): maj["prenom"] = request.form["prenom"].strip()
        if request.form.get("cne"):    maj["cne"]    = request.form["cne"].strip()
        if request.form.get("groupe_id"):
            nouveau_gid = ObjectId(request.form["groupe_id"])
            if not db["groupes"].find_one({"_id": nouveau_gid}):
                return jsonify({"error": "Nouveau groupe introuvable"}), 404
            maj["groupe_id"] = nouveau_gid

        if "photo" in request.files and request.files["photo"].filename:
            try:
                photo_b64, embedding = photo_vers_base64_et_embedding(request.files["photo"])
                maj["photo_base64"] = photo_b64
                maj["embedding"]    = embedding
            except Exception as e:
                return jsonify({"error": f"Erreur traitement photo : {str(e)}"}), 500
    else:
        data = request.json or {}
        if "nom"       in data: maj["nom"]       = data["nom"].strip()
        if "prenom"    in data: maj["prenom"]    = data["prenom"].strip()
        if "cne"       in data: maj["cne"]       = data["cne"].strip()
        if "groupe_id" in data:
            nouveau_gid = ObjectId(data["groupe_id"])
            if not db["groupes"].find_one({"_id": nouveau_gid}):
                return jsonify({"error": "Nouveau groupe introuvable"}), 404
            maj["groupe_id"] = nouveau_gid

    if not maj:
        return jsonify({"error": "Aucune donnée à modifier"}), 400

    db["etudiants"].update_one({"_id": ObjectId(etudiant_id)}, {"$set": maj})
    return jsonify({"message": "✅ Étudiant modifié"})


@admin_bp.route("/etudiants/<etudiant_id>", methods=["DELETE"])
def delete_etudiant(etudiant_id):
    db = get_db()
    db["etudiants"].delete_one({"_id": ObjectId(etudiant_id)})
    return jsonify({"message": "✅ Étudiant supprimé"})


# ══════════════════════════════════════════════════════════════════════════════
#  PROFESSEURS
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/professeurs", methods=["GET"])
def get_professeurs():
    db     = get_db()
    result = []
    for p in db["professeurs"].find():
        pid = str(p["_id"])
        result.append({
            "id":          pid,
            "nom":         p["nom"],
            "prenom":      p["prenom"],
            "matiere":     p.get("matiere", ""),
            "a_embedding": p.get("embedding") is not None,
            "a_photo":     p.get("photo_base64") is not None,
            # ✅ FIX PHOTOS : route qui sert la photo depuis MongoDB base64
            "photo_url":   f"/admin/photos/prof/{pid}" if p.get("photo_base64") else None
        })
    return jsonify({"professeurs": result, "total": len(result)})


@admin_bp.route("/professeurs", methods=["POST"])
def add_professeur():
    db = get_db()

    nom     = (request.form.get("nom")     or "").strip()
    prenom  = (request.form.get("prenom")  or "").strip()
    matiere = (request.form.get("matiere") or "").strip()

    if not nom or not prenom or not matiere:
        return jsonify({"error": "'nom', 'prenom', 'matiere' sont requis"}), 400

    photo_b64 = None
    embedding = None

    if "photo" in request.files and request.files["photo"].filename:
        try:
            photo_b64, embedding = photo_vers_base64_et_embedding(request.files["photo"])
        except Exception as e:
            return jsonify({"error": f"Erreur traitement photo : {str(e)}"}), 500

    r = db["professeurs"].insert_one({
        "nom":          nom,
        "prenom":       prenom,
        "matiere":      matiere,
        "photo_base64": photo_b64,
        "embedding":    embedding,
        "creee_le":     datetime.now()
    })

    msg = "✅ Professeur ajouté avec embedding" if embedding else "✅ Professeur ajouté (sans photo)"
    return jsonify({"message": msg, "id": str(r.inserted_id)}), 201


@admin_bp.route("/professeurs/<prof_id>", methods=["PUT"])
def update_professeur(prof_id):
    db  = get_db()
    maj = {}

    if request.content_type and "multipart" in request.content_type:
        if request.form.get("nom"):     maj["nom"]     = request.form["nom"].strip()
        if request.form.get("prenom"):  maj["prenom"]  = request.form["prenom"].strip()
        if request.form.get("matiere"): maj["matiere"] = request.form["matiere"].strip()

        if "photo" in request.files and request.files["photo"].filename:
            try:
                photo_b64, embedding = photo_vers_base64_et_embedding(request.files["photo"])
                maj["photo_base64"] = photo_b64
                maj["embedding"]    = embedding
            except Exception as e:
                return jsonify({"error": f"Erreur traitement photo : {str(e)}"}), 500
    else:
        data = request.json or {}
        if "nom"     in data: maj["nom"]     = data["nom"].strip()
        if "prenom"  in data: maj["prenom"]  = data["prenom"].strip()
        if "matiere" in data: maj["matiere"] = data["matiere"].strip()

    if not maj:
        return jsonify({"error": "Aucune donnée à modifier"}), 400

    db["professeurs"].update_one({"_id": ObjectId(prof_id)}, {"$set": maj})
    return jsonify({"message": "✅ Professeur modifié"})


@admin_bp.route("/professeurs/<prof_id>", methods=["DELETE"])
def delete_professeur(prof_id):
    db = get_db()
    db["professeurs"].delete_one({"_id": ObjectId(prof_id)})
    return jsonify({"message": "✅ Professeur supprimé"})


# ══════════════════════════════════════════════════════════════════════════════
#  JUSTIFICATIONS  ✅ NOUVEAU
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/justifications", methods=["GET"])
def get_justifications():
    """
    Retourne toutes les demandes de justification soumises par étudiants et profs.
    Chaque justification est une absence + motif stockés dans la collection
    'justifications' (créée automatiquement).
    """
    db     = get_db()
    result = []

    for j in db["justifications"].find().sort("date_soumission", -1):
        # Récupérer infos de la personne
        person = None
        type_p = j.get("type", "etudiant")
        if type_p == "etudiant":
            person = db["etudiants"].find_one({"_id": j.get("personne_id")})
        else:
            person = db["professeurs"].find_one({"_id": j.get("personne_id")})

        result.append({
            "id":              str(j["_id"]),
            "personne_id":     str(j.get("personne_id", "")),
            "type":            type_p,
            "nom":             person["nom"]    if person else "Inconnu",
            "prenom":          person["prenom"] if person else "",
            "date_absence":    j.get("date_absence", ""),
            "motif":           j.get("motif", ""),
            "statut":          j.get("statut", "en_attente"),
            "date_soumission": str(j.get("date_soumission", ""))
        })

    return jsonify({"justifications": result, "total": len(result)})


@admin_bp.route("/justifications/<justif_id>", methods=["PUT"])
def traiter_justification(justif_id):
    """
    Body JSON : { "statut": "accepte" | "refuse" }
    Met à jour le statut de la justification.
    Si acceptée → marque l'absence comme justifiée dans presences.
    """
    db   = get_db()
    data = request.json or {}
    statut = data.get("statut", "").strip()

    if statut not in ("accepte", "refuse"):
        return jsonify({"error": "Statut invalide : 'accepte' ou 'refuse'"}), 400

    justif = db["justifications"].find_one({"_id": ObjectId(justif_id)})
    if not justif:
        return jsonify({"error": "Justification introuvable"}), 404

    db["justifications"].update_one(
        {"_id": ObjectId(justif_id)},
        {"$set": {"statut": statut, "traite_le": datetime.now()}}
    )

    # Si acceptée → justifier l'absence dans presences
    if statut == "accepte" and justif.get("seance_id") and justif.get("personne_id"):
        db["presences"].update_one(
            {
                "seance_id":   justif["seance_id"],
                "personne_id": justif["personne_id"]
            },
            {"$set": {"justifie": True, "motif": justif.get("motif", "")}}
        )

    msg = "✅ Justification acceptée" if statut == "accepte" else "✅ Justification refusée"
    return jsonify({"message": msg})


# ══════════════════════════════════════════════════════════════════════════════
#  GÉNÉRATION DES SÉANCES DU JOUR  ✅ NOUVEAU
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/generer-seances", methods=["POST"])
def generer_seances():
    """
    Génère automatiquement les séances du jour pour tous les groupes
    qui ont un emploi du temps configuré.

    Stratégie :
    - Lit la collection 'planning_hebdo' (optionnelle) pour des créneaux fixes.
    - Si aucun planning_hebdo : reporte les séances "en_attente" d'hier sur aujourd'hui.
    - Ignore les groupes sans emploi du temps.
    - Retourne le nombre de séances créées / déjà existantes.

    Body JSON optionnel : { "date": "YYYY-MM-DD" }  (défaut = aujourd'hui)
    """
    db   = get_db()
    # ✅ FIX 415 : force=True ignore le Content-Type manquant, silent=True évite le crash
    data = request.get_json(force=True, silent=True) or {}
    date_cible = data.get("date") or datetime.now().strftime("%Y-%m-%d")

    # Jour de la semaine en français (pour planning_hebdo)
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    dt = datetime.strptime(date_cible, "%Y-%m-%d")
    jour_semaine = jours[dt.weekday()]

    groupes = list(db["groupes"].find({"emploi_du_temps": {"$ne": None}}))
    crees   = 0
    ignores = 0

    for groupe in groupes:
        # ── Méthode 1 : collection planning_hebdo ─────────────────────────
        # Format : { groupe_id, jour, heure_debut, heure_fin, matiere,
        #            prof_id, salle_id }
        creneaux = list(db["planning_hebdo"].find({
            "groupe_id": groupe["_id"],
            "jour":      jour_semaine
        }))

        # ── Méthode 2 : fallback — reporter les créneaux d'une semaine type
        if not creneaux:
            # Chercher des séances passées de ce groupe comme template
            # (même jour de la semaine, semaine précédente)
            date_ref = (dt - timedelta(days=7)).strftime("%Y-%m-%d")
            creneaux_ref = list(db["seances"].find({
                "groupe_id": groupe["_id"],
                "date":      date_ref
            }))
            # Convertir en format planning_hebdo
            creneaux = [{
                "groupe_id":   s["groupe_id"],
                "matiere":     s.get("matiere", ""),
                "heure_debut": s.get("heure_debut", ""),
                "heure_fin":   s.get("heure_fin", ""),
                "prof_id":     s.get("prof_id"),
                "salle_id":    s.get("salle_id"),
            } for s in creneaux_ref]

        for creneau in creneaux:
            if not creneau.get("salle_id") or not creneau.get("heure_debut"):
                ignores += 1
                continue

            # Vérifier si la séance existe déjà pour ce groupe/date/heure
            existante = db["seances"].find_one({
                "groupe_id":   groupe["_id"],
                "date":        date_cible,
                "heure_debut": creneau["heure_debut"]
            })
            if existante:
                ignores += 1
                continue

            # Vérifier conflit de salle
            conflit = db["seances"].find_one({
                "salle_id": creneau["salle_id"],
                "date":     date_cible,
                "$or": [{
                    "heure_debut": {"$lt": creneau.get("heure_fin", "23:59")},
                    "heure_fin":   {"$gt": creneau["heure_debut"]}
                }]
            })
            if conflit:
                ignores += 1
                continue

            db["seances"].insert_one({
                "groupe_id":   groupe["_id"],
                "prof_id":     creneau.get("prof_id"),
                "salle_id":    creneau["salle_id"],
                "matiere":     creneau.get("matiere", "—"),
                "date":        date_cible,
                "heure_debut": creneau["heure_debut"],
                "heure_fin":   creneau.get("heure_fin", ""),
                "statut":      "en_attente",
                "status":      "en_attente",   # compatibilité camera.py
                "creee_le":    datetime.now()
            })
            crees += 1

    msg = (
        f"✅ {crees} séance(s) générée(s) pour le {date_cible}"
        if crees > 0
        else f"ℹ️  Aucune nouvelle séance à générer pour le {date_cible} ({ignores} déjà existante(s))"
    )
    return jsonify({
        "message":        msg,
        "seances_creees": crees,
        "ignores":        ignores,
        "date":           date_cible,
        "jour":           jour_semaine
    })


# ══════════════════════════════════════════════════════════════════════════════
#  ARCHIVAGE  ✅ NOUVEAU
# ══════════════════════════════════════════════════════════════════════════════

@admin_bp.route("/archiver-rapports", methods=["POST"])
def archiver_rapports():
    """
    Archive les rapports des séances terminées datant de plus de 48h.
    - Copie dans la collection 'archives'
    - Supprime les séances archivées de la collection 'seances'
    - Conserve les présences (elles ne sont jamais supprimées)
    """
    db          = get_db()
    seuil       = datetime.now() - timedelta(hours=48)
    seuil_date  = seuil.strftime("%Y-%m-%d")

    # Séances terminées il y a plus de 48h
    seances_old = list(db["seances"].find({
        "date": {"$lte": seuil_date},
        "$or": [
            {"statut": "termine"},
            {"status": "termine"},
            {"statut": {"$exists": False}}
        ]
    }))

    if not seances_old:
        return jsonify({"message": "ℹ️  Aucune séance à archiver (< 48h ou déjà archivées)"})

    archivees = 0
    for seance in seances_old:
        groupe         = db["groupes"].find_one({"_id": seance.get("groupe_id")})
        prof           = db["professeurs"].find_one({"_id": seance.get("prof_id")})
        salle          = db["salles"].find_one({"_id": seance.get("salle_id")})
        tous_etudiants = list(db["etudiants"].find({"groupe_id": seance.get("groupe_id")}))
        presences_docs = list(db["presences"].find({"seance_id": seance["_id"]}))

        ids_presents = {
            str(p["personne_id"]) for p in presences_docs if p["statut"] == "present"
        }

        presents = [
            {"id": str(e["_id"]), "nom": e["nom"], "prenom": e["prenom"]}
            for e in tous_etudiants if str(e["_id"]) in ids_presents
        ]
        absents = [
            {"id": str(e["_id"]), "nom": e["nom"], "prenom": e["prenom"]}
            for e in tous_etudiants if str(e["_id"]) not in ids_presents
        ]

        total = len(tous_etudiants)
        taux  = f"{(len(presents)/total*100):.1f}%" if total > 0 else "0%"

        # Vérifier si déjà archivée
        if db["archives"].find_one({"seance_id": seance["_id"]}):
            continue

        db["archives"].insert_one({
            "seance_id":    seance["_id"],
            "groupe_id":    seance.get("groupe_id"),
            "groupe":       groupe["nom"] if groupe else "?",
            "matiere":      seance.get("matiere", ""),
            "date":         seance.get("date", ""),
            "heure_debut":  seance.get("heure_debut", ""),
            "heure_fin":    seance.get("heure_fin", ""),
            "salle":        salle["num_salle"] if salle else "?",
            "prof":         f"{prof['nom']} {prof['prenom']}" if prof else "?",
            "prof_present": str(seance.get("prof_id", "")) in ids_presents,
            "nb_presents":  len(presents),
            "nb_absents":   len(absents),
            "taux_presence": taux,
            "presents":     presents,
            "absents":      absents,
            "archive_le":   datetime.now()
        })

        # Supprimer la séance (les présences sont conservées)
        db["seances"].delete_one({"_id": seance["_id"]})
        archivees += 1

    return jsonify({
        "message": f"✅ {archivees} séance(s) archivée(s)",
        "archivees": archivees
    })


@admin_bp.route("/archives", methods=["GET"])
def get_archives():
    """
    Query params (optionnels) :
      ?date=YYYY-MM-DD   — filtrer par date exacte
      ?month=MM          — filtrer par mois (année courante)
    """
    db    = get_db()
    filtre = {}

    date  = request.args.get("date")
    month = request.args.get("month")

    if date:
        filtre["date"] = date
    elif month:
        annee = datetime.now().year
        filtre["date"] = {
            "$gte": f"{annee}-{month}-01",
            "$lte": f"{annee}-{month}-31"
        }

    archives = []
    for a in db["archives"].find(filtre).sort("date", -1):
        archives.append({
            "id":           str(a["_id"]),
            "seance_id":    str(a.get("seance_id", "")),
            "matiere":      a.get("matiere", ""),
            "groupe":       a.get("groupe", "?"),
            "date":         a.get("date", ""),
            "heure_debut":  a.get("heure_debut", ""),
            "heure_fin":    a.get("heure_fin", ""),
            "nb_presents":  a.get("nb_presents", 0),
            "nb_absents":   a.get("nb_absents", 0),
            "taux_presence": a.get("taux_presence", "0%"),
            "prof_present": a.get("prof_present", False),
            "archive_le":   str(a.get("archive_le", ""))
        })

    return jsonify({"archives": archives, "total": len(archives)})


# ══════════════════════════════════════════════════════════════════════════════
#  SERVING PHOTOS DEPUIS MONGODB  ✅ FIX 404 PHOTOS
# ══════════════════════════════════════════════════════════════════════════════
#
#  Les photos sont stockées en base64 dans MongoDB (champ photo_base64).
#  Ces routes les servent comme de vraies images HTTP.
#  Le frontend appelle : /admin/photos/etudiant/<id>  ou  /admin/photos/prof/<id>
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/photos/etudiant/<etudiant_id>", methods=["GET"])
def photo_etudiant(etudiant_id):
    """Sert la photo d'un étudiant stockée en base64 dans MongoDB."""
    db = get_db()
    try:
        etu = db["etudiants"].find_one(
            {"_id": ObjectId(etudiant_id)},
            {"photo_base64": 1}
        )
    except Exception:
        return Response("ID invalide", status=400)

    if not etu or not etu.get("photo_base64"):
        return Response("Photo introuvable", status=404)

    try:
        img_bytes = base64.b64decode(etu["photo_base64"])
        return Response(
            img_bytes,
            mimetype="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(img_bytes))
            }
        )
    except Exception as e:
        return Response(f"Erreur décodage : {e}", status=500)


@admin_bp.route("/photos/prof/<prof_id>", methods=["GET"])
def photo_prof(prof_id):
    """Sert la photo d'un professeur stockée en base64 dans MongoDB."""
    db = get_db()
    try:
        prof = db["professeurs"].find_one(
            {"_id": ObjectId(prof_id)},
            {"photo_base64": 1}
        )
    except Exception:
        return Response("ID invalide", status=400)

    if not prof or not prof.get("photo_base64"):
        return Response("Photo introuvable", status=404)

    try:
        img_bytes = base64.b64decode(prof["photo_base64"])
        return Response(
            img_bytes,
            mimetype="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(img_bytes))
            }
        )
    except Exception as e:
        return Response(f"Erreur décodage : {e}", status=500)