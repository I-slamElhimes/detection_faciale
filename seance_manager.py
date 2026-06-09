# seance_manager.py
from db_config import get_db
from datetime import datetime
from bson.objectid import ObjectId

db = get_db()

def creer_seance(groupe_id, prof_id, salle_id, matiere, date_str, h_debut, h_fin):
    seance = {
        "groupe_id": ObjectId(groupe_id) if isinstance(groupe_id, str) else groupe_id,
        "prof_id":   ObjectId(prof_id)   if isinstance(prof_id, str)   else prof_id,
        "salle_id":  ObjectId(salle_id)  if isinstance(salle_id, str)  else salle_id,
        "matiere":   matiere,
        "date":      date_str,
        "heure_debut": h_debut,
        "heure_fin":   h_fin,
        "status":    "en_attente",
        "creee_le":  datetime.now()
    }
    result = db["seances"].insert_one(seance)
    print(f"✅ Séance créée (ID: {result.inserted_id})")
    print(f"   Matière : {matiere} | Date : {date_str} | {h_debut}→{h_fin}")
    return result.inserted_id


def get_seance_active_par_salle(num_salle):
    """
    Cherche la séance active en ce moment dans une salle donnée.
    ✅ Accepte les séances avec OU sans champ 'status'.
    """
    salle = db["salles"].find_one({"num_salle": num_salle})
    if not salle:
        print(f"❌ Salle '{num_salle}' introuvable dans MongoDB.")
        return None

    maintenant = datetime.now()
    date_j     = maintenant.strftime("%Y-%m-%d")
    heure_j    = maintenant.strftime("%H:%M")

    seance = db["seances"].find_one({
        "salle_id":    salle["_id"],
        "date":        date_j,
        "heure_debut": {"$lte": heure_j},
        "heure_fin":   {"$gte": heure_j},
        # ✅ CORRECTION : accepte "en_attente", "en_cours", ou pas de champ status du tout
        "$or": [
            {"status": {"$in": ["en_attente", "en_cours"]}},
            {"status": {"$exists": False}}
        ]
    })
    return seance

def lister_seances_du_jour():
    today   = datetime.now().strftime("%Y-%m-%d")
    seances = list(db["seances"].find({"date": today}))
    print(f"\n📅 Séances du {today} ({len(seances)} séance(s)) :")
    for s in seances:
        salle  = db["salles"].find_one({"_id": s.get("salle_id")})
        groupe = db["groupes"].find_one({"_id": s.get("groupe_id")})
        print(
            f"  - {s.get('matiere')} | {s['heure_debut']}→{s['heure_fin']} "
            f"| {salle['num_salle'] if salle else 'Salle?'} "
            f"| {groupe['nom'] if groupe else 'Groupe?'} "
            f"| Status: {s.get('status', 'N/A')}"
        )


def supprimer_seances_passees():
    aujourd_hui = datetime.now().strftime("%Y-%m-%d")
    result = db["seances"].delete_many({"date": {"$lt": aujourd_hui}})
    print(f"🧹 {result.deleted_count} ancienne(s) séance(s) supprimée(s).")


if __name__ == "__main__":
    lister_seances_du_jour()