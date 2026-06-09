# db_config.py
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME   = "face_attendance"

def get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

# 10 collections exactement selon le plan
COLLECTIONS = {
    "administrateurs": "administrateurs",
    "filieres":        "filieres",
    "groupes":         "groupes",
    "salles":          "salles",
    "cameras":         "cameras",      # ← collection séparée (1 caméra = 1 salle)
    "etudiants":       "etudiants",
    "professeurs":     "professeurs",
    "seances":         "seances",      # ← supprimée après 20 min
    "presences":       "presences",    # ← conservée à vie
    "rapports":        "rapports",     # ← conservée à vie
}