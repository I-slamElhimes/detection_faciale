# add_prof.py
from db_config import get_db

db = get_db()
prof = {
    "nom": "Zaid",
    "prenom": "Omar",
    "matiere": "Intelligence Artificielle",
    "embedding": None, # Sera rempli par Islam
    "photo_path": "data/photos/profs/omar_zaid.jpg"
}
db["professeurs"].insert_one(prof)
print("✅ Professeur ajouté ! Ton rapport validate_db sera tout vert.")