# create_seance_test.py
# Crée une séance active MAINTENANT pour tester camera.py
from db_config import get_db
from datetime import datetime, timedelta

db = get_db()

groupe = db["groupes"].find_one({"nom": "Groupe-01"})
prof   = db["professeurs"].find_one({"nom": "Benali"})
salle  = db["salles"].find_one({"num_salle": "Salle-01"})
camera = db["cameras"].find_one({"salle_id": salle["_id"]}) if salle else None

if not groupe: print("❌ Lance seed_data.py d'abord !"); exit()
if not salle:  print("❌ Salle-01 introuvable !"); exit()
if not camera: print("❌ Caméra introuvable pour Salle-01 !"); exit()

now   = datetime.now()
debut = (now - timedelta(minutes=5)).strftime("%H:%M")
fin   = (now + timedelta(minutes=15)).strftime("%H:%M")
date  = now.strftime("%Y-%m-%d")

db["seances"].delete_many({"matiere": "TEST - IA"})

r = db["seances"].insert_one({
    "groupe_id":   groupe["_id"],
    "prof_id":     prof["_id"] if prof else None,
    "salle_id":    salle["_id"],
    "matiere":     "TEST - IA",
    "date":        date,
    "heure_debut": debut,
    "heure_fin":   fin,
    "creee_le":    datetime.now()
})

check = db["seances"].find_one({
    "salle_id":    salle["_id"],
    "date":        date,
    "heure_debut": {"$lte": now.strftime("%H:%M")},
    "heure_fin":   {"$gte": now.strftime("%H:%M")}
})

print("=" * 55)
print(f"✅ Séance créée : {r.inserted_id}")
print(f"   Salle   : {salle['num_salle']} (caméra webcam {camera['index_webcam']})")
print(f"   Groupe  : {groupe['nom']}")
print(f"   Horaire : {debut} → {fin}")
print(f"   Détectable par camera.py : {'✅ OUI' if check else '❌ NON'}")
if check:
    print(f"\n🚀 Lance : python camera.py --salle Salle-01")