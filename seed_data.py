# seed_data.py
# Insère les données de test selon le plan.
# Lance après create_collections.py

from db_config import get_db
from datetime import datetime
from bson.objectid import ObjectId

db = get_db()


def vider():
    for col in ["administrateurs","filieres","groupes","salles","cameras",
                "etudiants","professeurs","seances","presences","rapports"]:
        db[col].delete_many({})
    print("🧹 Toutes les collections vidées.\n")


def seed():
    print("=" * 55)
    print("   SEED — DONNÉES DE TEST")
    print("=" * 55)

    # ── ADMIN ─────────────────────────────────────────────────────────────
    db["administrateurs"].insert_one({
        "nom":      "Admin",
        "prenom":   "Principal",
        "username": "admin",
        "password": "admin123",    # hasher en production
        "role":     "admin",
        "creee_le": datetime.now()
    })
    print("\n✅ Admin   → username: admin / password: admin123")

    # ── FILIÈRE ───────────────────────────────────────────────────────────
    f = db["filieres"].insert_one({
        "nom":         "IA & Big Data",
        "description": "Filière Intelligence Artificielle et Big Data",
        "creee_le":    datetime.now()
    })
    fid = f.inserted_id
    print(f"✅ Filière → 'IA & Big Data'  (ID: {fid})")

    # ── GROUPES ───────────────────────────────────────────────────────────
    g1 = db["groupes"].insert_one({
        "nom":             "Groupe-01",
        "filiere_id":      fid,
        "emploi_du_temps": None,    # l'admin uploadera le PDF plus tard
        "creee_le":        datetime.now()
    })
    g2 = db["groupes"].insert_one({
        "nom":             "Groupe-02",
        "filiere_id":      fid,
        "emploi_du_temps": None,
        "creee_le":        datetime.now()
    })
    g1id = g1.inserted_id
    g2id = g2.inserted_id
    print(f"✅ Groupe  → Groupe-01  (ID: {g1id})")
    print(f"✅ Groupe  → Groupe-02  (ID: {g2id})")

    # ── SALLES ────────────────────────────────────────────────────────────
    s1 = db["salles"].insert_one({
        "num_salle":   "Salle-01",
        "description": "Salle informatique principale",
        "creee_le":    datetime.now()
    })
    s2 = db["salles"].insert_one({
        "num_salle":   "Salle-02",
        "description": "Salle de cours secondaire",
        "creee_le":    datetime.now()
    })
    s1id = s1.inserted_id
    s2id = s2.inserted_id
    print(f"✅ Salle   → Salle-01   (ID: {s1id})")
    print(f"✅ Salle   → Salle-02   (ID: {s2id})")

    # ── CAMERAS (collection séparée, 1 caméra = 1 salle) ─────────────────
    #
    #  salle_id        : lien vers la salle (FK unique)
    #  index_webcam    : numéro webcam locale (0 = 1ère webcam du PC)
    #  ip              : URL RTSP si caméra réseau, None sinon
    #  seuil_cosinus   : seuil de reconnaissance (plan : défaut 0.40)
    #  duree_detection : secondes (plan : défaut 1200 = 20 min)
    #  actif           : False au départ, passe True quand camera.py démarre
    #
    c1 = db["cameras"].insert_one({
        "salle_id":        s1id,
        "index_webcam":    0,        # première webcam du PC
        "ip":              None,     # None = webcam locale
        "seuil_cosinus":   0.40,     # selon plan
        "duree_detection": 1200,     # 20 min en secondes selon plan
        "actif":           False,    # selon plan : défaut false
        "creee_le":        datetime.now()
    })
    c2 = db["cameras"].insert_one({
        "salle_id":        s2id,
        "index_webcam":    1,        # deuxième webcam
        "ip":              None,
        "seuil_cosinus":   0.40,
        "duree_detection": 1200,
        "actif":           False,
        "creee_le":        datetime.now()
    })
    print(f"✅ Caméra  → Salle-01 (webcam 0)  (ID: {c1.inserted_id})")
    print(f"✅ Caméra  → Salle-02 (webcam 1)  (ID: {c2.inserted_id})")

    # ── PROFESSEURS ───────────────────────────────────────────────────────
    # photo_base64 et embedding sont None → register_face.py les remplira
    p1 = db["professeurs"].insert_one({
        "nom":          "Benali",
        "prenom":       "Mohammed",
        "matiere":      "Intelligence Artificielle",   # singulier selon plan
        "photo_base64": None,    # ← register_face.py remplira
        "embedding":    None,    # ← register_face.py remplira
        "creee_le":     datetime.now()
    })
    p2 = db["professeurs"].insert_one({
        "nom":          "Chraibi",
        "prenom":       "Fatima",
        "matiere":      "Réseaux",
        "photo_base64": None,
        "embedding":    None,
        "creee_le":     datetime.now()
    })
    p1id = p1.inserted_id
    p2id = p2.inserted_id
    print(f"✅ Prof    → Benali Mohammed  (ID: {p1id})")
    print(f"✅ Prof    → Chraibi Fatima   (ID: {p2id})")

    # ── ÉTUDIANTS Groupe-01 ───────────────────────────────────────────────
    # photo_base64 : stockée dans MongoDB (jamais sur disque selon plan)
    # embedding    : Float[512] — None avant register_face.py
    print("\n  👥 Étudiants Groupe-01 :")
    for d in [
        {"nom": "Alami",   "prenom": "Youssef", "cne": "E100001"},
        {"nom": "Bakkali", "prenom": "Sara",     "cne": "E100002"},
        {"nom": "Chaouqi", "prenom": "Amine",    "cne": "E100003"},
    ]:
        e = db["etudiants"].insert_one({
            **d,
            "groupe_id":    g1id,
            "photo_base64": None,    # ← register_face.py remplira
            "embedding":    None,    # ← Float[512] après register_face.py
            "creee_le":     datetime.now()
        })
        print(f"     {d['prenom']:10} {d['nom']:10} (ID: {e.inserted_id})")

    # ── ÉTUDIANTS Groupe-02 ───────────────────────────────────────────────
    print("\n  👥 Étudiants Groupe-02 :")
    for d in [
        {"nom": "Daoudi",   "prenom": "Nadia",  "cne": "E200001"},
        {"nom": "El Fassi", "prenom": "Karim",  "cne": "E200002"},
    ]:
        e = db["etudiants"].insert_one({
            **d,
            "groupe_id":    g2id,
            "photo_base64": None,
            "embedding":    None,
            "creee_le":     datetime.now()
        })
        print(f"     {d['prenom']:10} {d['nom']:10} (ID: {e.inserted_id})")

    # ── RÉSUMÉ ────────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("✅ Seed terminé !")
    print("=" * 55)
    print("\n📋 Prochaine étape :")
    print("   → python validate_db.py")
    print("   → python create_seance_test.py")
    print("   → python register_face.py  (ajouter les embeddings)")


if __name__ == "__main__":
    vider()
    seed()