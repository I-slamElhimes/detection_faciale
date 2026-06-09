# queries/presence_manager.py
from db_config import get_db
from datetime import datetime
from bson.objectid import ObjectId

def marquer_present(seance_id, personne_id, type_personne):
    """
    Islam appellera cette fonction dès qu'un visage est reconnu.
    type_personne: "etudiant" ou "professeur"
    """
    db = get_db()
    presence = {
        "seance_id": ObjectId(seance_id),
        "personne_id": ObjectId(personne_id),
        "type": type_personne,
        "heure_arrivee": datetime.now().strftime("%H:%M"),
        "statut": "present"
    }
    # upsert=True : si la présence existe déjà, on ne la recrée pas
    db["presences"].update_one(
        {"seance_id": ObjectId(seance_id), "personne_id": ObjectId(personne_id)},
        {"$set": presence},
        upsert=True
    )
    print(f"📍 Présence enregistrée pour {personne_id}")