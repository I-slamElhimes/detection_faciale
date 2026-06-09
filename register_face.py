# register_face.py
# Enregistre les embeddings ArcFace et les photos (base64) dans MongoDB.
# À utiliser UNE FOIS par personne, avant de lancer la caméra.

import sys
import os
import base64
sys.path.insert(0, os.path.dirname(__file__))

from db_config import get_db
from utils.embedding import extraire_embedding
from bson.objectid import ObjectId


def photo_vers_base64(photo_path):
    """Lit une image depuis le disque et la convertit en base64."""
    with open(photo_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def enregistrer_etudiant(etudiant_id, photo_path):
    """
    Extrait l'embedding ArcFace d'une photo et le sauvegarde dans MongoDB
    avec la photo encodée en base64.
    Plus besoin de garder la photo sur le disque après ça.
    """
    db = get_db()
    print(f"📸 Extraction embedding étudiant : {photo_path}")
    embedding   = extraire_embedding(photo_path)
    photo_b64   = photo_vers_base64(photo_path)

    db["etudiants"].update_one(
        {"_id": ObjectId(etudiant_id)},
        {"$set": {
            "embedding":    embedding,
            "photo_base64": photo_b64
        }}
    )
    print(f"✅ Étudiant enregistré ({len(embedding)} dimensions)")


def enregistrer_prof(prof_id, photo_path):
    """Même chose pour un professeur."""
    db = get_db()
    print(f"📸 Extraction embedding professeur : {photo_path}")
    embedding   = extraire_embedding(photo_path)
    photo_b64   = photo_vers_base64(photo_path)

    db["professeurs"].update_one(
        {"_id": ObjectId(prof_id)},
        {"$set": {
            "embedding":    embedding,
            "photo_base64": photo_b64
        }}
    )
    print(f"✅ Professeur enregistré ({len(embedding)} dimensions)")


def lister_personnes_sans_embedding():
    """Affiche qui n'a pas encore d'embedding dans MongoDB."""
    db = get_db()
    etudiants = list(db["etudiants"].find({"embedding": None}))
    profs      = list(db["professeurs"].find({"embedding": None}))

    print("\n📋 Personnes sans embedding :")
    print(f"  Étudiants ({len(etudiants)}) :")
    for e in etudiants:
        print(f"    - {e['nom']} {e['prenom']} | ID: {e['_id']}")
    print(f"  Professeurs ({len(profs)}) :")
    for p in profs:
        print(f"    - {p['nom']} {p['prenom']} | ID: {p['_id']}")


if __name__ == "__main__":
    # 1. Voir qui n'a pas encore d'embedding
    lister_personnes_sans_embedding()

    # 2. Pour enregistrer, dé-commenter les lignes ci-dessous
    #    et remplacer par les vrais IDs (affichés par seed_data.py)
    #
    # enregistrer_etudiant("ID_ETUDIANT_ICI", "data/photos/islam.jpg")
    # enregistrer_etudiant("ID_ETUDIANT_ICI", "data/photos/ahmed.jpg")
    # enregistrer_prof("ID_PROF_ICI",         "data/photos/zaid.jpg")