# test_endpoints.py
import requests
import json

BASE = "http://127.0.0.1:5000"

# ─────────────────────────────
# 1. Créer une séance de test
# ─────────────────────────────
from db_config import get_db
from bson.objectid import ObjectId
from datetime import datetime

db = get_db()
groupe = db["groupes"].find_one()
prof = db["professeurs"].find_one()
etudiant = db["etudiants"].find_one()

# Créer une séance pour aujourd'hui
seance = {
    "groupe_id": groupe["_id"],
    "prof_id": prof["_id"],
    "matiere": "Intelligence Artificielle",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "heure_debut": "08:00",
    "heure_fin": "22:00",
}
seance_id = str(db["seances"].insert_one(seance).inserted_id)
etudiant_id = str(etudiant["_id"])

print(f"✅ Séance créée : {seance_id}")
print(f"✅ Étudiant ID  : {etudiant_id}")

# ─────────────────────────────
# 2. POST /presences
# ─────────────────────────────
print("\n📤 Test POST /presences :")
r = requests.post(f"{BASE}/presences", json={
    "seance_id": seance_id,
    "personne_id": etudiant_id,
    "type": "etudiant",
    "statut": "present"
})
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# ─────────────────────────────
# 3. GET /presences/<seance_id>
# ─────────────────────────────
print("\n📥 Test GET /presences :")
r = requests.get(f"{BASE}/presences/{seance_id}")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# ─────────────────────────────
# 4. GET /rapport/<seance_id>
# ─────────────────────────────
print("\n📊 Test GET /rapport :")
r = requests.get(f"{BASE}/rapport/{seance_id}")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))