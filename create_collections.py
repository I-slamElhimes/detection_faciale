# create_collections.py
# Lance UNE SEULE FOIS pour créer les 10 collections et les indexes.
from pymongo import MongoClient, ASCENDING

MONGO_URI = "mongodb://localhost:27017"
DB_NAME   = "face_attendance"

def init_database():
    client = MongoClient(MONGO_URI)
    db     = client[DB_NAME]

    print("=" * 55)
    print("   INITIALISATION — 10 COLLECTIONS")
    print("=" * 55)

    # ── 1. CRÉER LES 10 COLLECTIONS ───────────────────────────────────────
    collections = [
        "administrateurs",
        "filieres",
        "groupes",
        "salles",
        "cameras",       # ← NOUVEAU  : 1 caméra = 1 salle (relation 1→1)
        "etudiants",
        "professeurs",
        "seances",       # ← supprimée après 20 min de détection
        "presences",     # ← conservée à vie
        "rapports",      # ← NOUVEAU  : conservé à vie
    ]

    existantes = db.list_collection_names()
    for col in collections:
        if col not in existantes:
            db.create_collection(col)
            print(f"  ✅ '{col}' créée.")
        else:
            print(f"  ℹ️  '{col}' existe déjà.")

    # ── 2. INDEX ──────────────────────────────────────────────────────────
    print("\n  📌 Création des index...")

    # administrateurs.username — unique (login)
    db["administrateurs"].create_index("username", unique=True)
    print("  ✅ administrateurs.username (unique)")

    # salles.num_salle — unique
    db["salles"].create_index("num_salle", unique=True)
    print("  ✅ salles.num_salle (unique)")

    # cameras.salle_id — unique (1 caméra = 1 salle)
    db["cameras"].create_index("salle_id", unique=True)
    print("  ✅ cameras.salle_id (unique)")

    # etudiants.groupe_id — index clé de filtrage
    db["etudiants"].create_index("groupe_id")
    print("  ✅ etudiants.groupe_id (index)")

    # seances : index composé (salle_id + date + heure_debut) ← CRITIQUE caméra
    db["seances"].create_index(
        [("salle_id", ASCENDING), ("date", ASCENDING), ("heure_debut", ASCENDING)]
    )
    print("  ✅ seances (salle_id + date + heure_debut) ← index critique caméra")

    # seances : index secondaire par date
    db["seances"].create_index([("date", ASCENDING), ("heure_debut", ASCENDING)])
    print("  ✅ seances (date + heure_debut)")

    # presences : unique (seance_id + personne_id) — anti-doublon
    db["presences"].create_index(
        [("seance_id", ASCENDING), ("personne_id", ASCENDING)],
        unique=True
    )
    print("  ✅ presences (seance_id + personne_id) unique")

    # rapports : index par seance_id
    db["rapports"].create_index("seance_id")
    print("  ✅ rapports.seance_id (index)")

    # ── 3. RÉSUMÉ ─────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  ✅ 10 collections créées avec succès !")
    print("=" * 55)
    print("""
  SCHEMA EXACT (selon plan) :

  administrateurs → _id, nom, prenom, username, password, role
  filieres        → _id, nom, description
  groupes         → _id, nom, filiere_id(FK), emploi_du_temps(Binary)
  salles          → _id, num_salle(unique), description
  cameras         → _id, salle_id(FK unique), seuil_cosinus,
                        duree_detection, actif
  etudiants       → _id, nom, prenom, groupe_id(FK), photo_base64,
                        embedding[512]
  professeurs     → _id, nom, prenom, matiere, photo_base64,
                        embedding[512]
  seances         → _id, groupe_id(FK), prof_id(FK), salle_id(FK),
                        matiere, date, heure_debut, heure_fin, creee_le
  presences       → _id, seance_id(FK), personne_id(FK), rapport_id(FK),
                        type, statut, heure_arrivee, justifie, motif
  rapports        → _id, seance_id(FK), groupe_id(FK), date, matiere,
                        nb_presents, nb_absents, taux_presence,
                        prof_present, presents[], absents[],
                        statut, genere_le
    """)
    print("  → Prochaine étape : python seed_data.py")


if __name__ == "__main__":
    init_database()