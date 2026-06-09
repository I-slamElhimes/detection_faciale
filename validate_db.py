# validate_db.py
# Vérifie que les 10 collections sont correctement remplies.
from db_config import get_db
from datetime import datetime

db = get_db()

def valider():
    print("=" * 55)
    print("   VALIDATION — 10 COLLECTIONS")
    print("=" * 55)

    # ── 1. COMPTER LES DOCUMENTS ──────────────────────────────────────────
    print()
    cols = {
        "administrateurs": "👤 Admins",
        "filieres":        "🏫 Filières",
        "groupes":         "👥 Groupes",
        "salles":          "🚪 Salles",
        "cameras":         "🎥 Caméras",
        "professeurs":     "👨‍🏫 Profs",
        "etudiants":       "🎓 Étudiants",
        "seances":         "📅 Séances",
        "presences":       "✅ Présences",
        "rapports":        "📊 Rapports",
    }
    ok = True
    for col, label in cols.items():
        n   = db[col].count_documents({})
        ico = "✅" if n > 0 else "⚠️ "
        if col not in ("seances","presences","rapports") and n == 0:
            ok = False
        print(f"  {ico} {label:<18} → {n}")

    # ── 2. VÉRIFIER CAMÉRAS ───────────────────────────────────────────────
    print("\n  🎥 Détail caméras :")
    for cam in db["cameras"].find():
        salle = db["salles"].find_one({"_id": cam["salle_id"]})
        nm    = salle["num_salle"] if salle else "?"
        src   = f"IP: {cam['ip']}" if cam.get("ip") else f"webcam index={cam.get('index_webcam','?')}"
        print(f"     {nm} | {src} | seuil={cam['seuil_cosinus']} | {cam['duree_detection']}s")

    # ── 3. VÉRIFIER EMBEDDINGS ────────────────────────────────────────────
    print("\n  🧠 Embeddings :")
    et = db["etudiants"].count_documents({})
    eo = db["etudiants"].count_documents({"embedding": {"$ne": None}})
    pt = db["professeurs"].count_documents({})
    po = db["professeurs"].count_documents({"embedding": {"$ne": None}})
    print(f"  {'✅' if eo==et and et>0 else '⚠️ '} Étudiants    {eo}/{et}")
    print(f"  {'✅' if po==pt and pt>0 else '⚠️ '} Professeurs  {po}/{pt}")
    if eo < et or po < pt:
        print("\n     → Lance register_face.py pour compléter les embeddings.")

    # ── 4. SÉANCE ACTIVE ──────────────────────────────────────────────────
    today   = datetime.now().strftime("%Y-%m-%d")
    heure_j = datetime.now().strftime("%H:%M")
    seances = list(db["seances"].find({"date": today}))
    print(f"\n  📅 Séances aujourd'hui ({today}) : {len(seances)}")
    for s in seances:
        salle  = db["salles"].find_one({"_id": s.get("salle_id")})
        groupe = db["groupes"].find_one({"_id": s.get("groupe_id")})
        active = s["heure_debut"] <= heure_j <= s["heure_fin"]
        ico    = "🟢 ACTIVE" if active else "⚪"
        print(f"     {ico} {s.get('matiere')} | {s['heure_debut']}→{s['heure_fin']} "
              f"| {salle['num_salle'] if salle else '?'} | {groupe['nom'] if groupe else '?'}")

    # ── 5. CONCLUSION ─────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    if ok and seances:
        print("🎉 Tout est prêt ! Lance : python camera.py --salle Salle-01")
    elif not ok:
        print("⚠️  Lance seed_data.py d'abord.")
    else:
        print("⚠️  Lance create_seance_test.py pour créer une séance de test.")
    print("=" * 55)

if __name__ == "__main__":
    valider()