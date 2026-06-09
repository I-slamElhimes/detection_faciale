# queries/seance_queries.py
from datetime import datetime
from db_config import get_db

def obtenir_seance_actuelle():
    db = get_db()
    maintenant = datetime.now()
    date_j = maintenant.strftime("%Y-%m-%d")
    heure_j = maintenant.strftime("%H:%M")

    # On cherche une séance pour aujourd'hui entre l'heure de début et de fin
    return db["seances"].find_one({
        "date": date_j,
        "heure_debut": {"$lte": heure_j},
        "heure_fin": {"$gte": heure_j}
    })