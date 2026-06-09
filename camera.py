# camera.py
# ─────────────────────────────────────────────────────────────────────────────
# Lancer : python camera.py --salle Salle-01
# La durée et le seuil viennent de MongoDB (collection cameras).
# ─────────────────────────────────────────────────────────────────────────────

import cv2
import requests
import time
import argparse
from datetime import datetime
from db_config import get_db
from seance_manager import get_seance_active_par_salle

API_URL = "http://127.0.0.1:5000"


# ── Argument CLI ──────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--salle", default="Salle-01", help="Numéro de salle (ex: Salle-01)")
args = parser.parse_args()
NUM_SALLE = args.salle


# ── Enregistrer une présence via l'API Flask ──────────────────────────────────
def enregistrer_presence(seance_id, personne_id, type_personne):
    try:
        requests.post(f"{API_URL}/presences", json={
            "seance_id":  seance_id,
            "personne_id": personne_id,
            "type":       type_personne,
            "statut":     "present"
        }, timeout=3)
    except Exception as e:
        print(f"⚠️  Erreur présence : {e}")


# ── Identifier un visage via l'API Flask ──────────────────────────────────────
def identifier_visage(frame, groupe_id, prof_id, salle_id):
    """
    Envoie le frame + groupe_id + prof_id + salle_id à /identifier.
    salle_id permet à identify.py de récupérer le seuil_cosinus de la caméra.
    """
    try:
        _, img_encoded = cv2.imencode(".jpg", frame)
        response = requests.post(
            f"{API_URL}/identifier",
            files={"image": ("frame.jpg", img_encoded.tobytes(), "image/jpeg")},
            data={
                "groupe_id": groupe_id,
                "prof_id":   prof_id,
                "salle_id":  salle_id      # ✅ CORRECTION — seuil depuis DB
            },
            timeout=5
        )
        return response.json()
    except Exception as e:
        print(f"⚠️  Erreur identification : {e}")
        return None


# ── Boucle principale ─────────────────────────────────────────────────────────
def demarrer_camera():
    db = get_db()

    print(f"\n🔍 Recherche d'une séance active pour '{NUM_SALLE}'...")

    # 1. Séance active ?
    seance = get_seance_active_par_salle(NUM_SALLE)
    if not seance:
        print("❌ Aucune séance active en ce moment.")
        return

    # 2. Salle + caméra
    salle = db["salles"].find_one({"num_salle": NUM_SALLE})
    if not salle:
        print(f"❌ Salle '{NUM_SALLE}' introuvable.")
        return

    camera_doc = db["cameras"].find_one({"salle_id": salle["_id"]})
    if not camera_doc:
        print(f"❌ Aucune caméra configurée pour '{NUM_SALLE}'.")
        return

    # 3. Paramètres depuis MongoDB (configurable par salle)
    index_webcam    = camera_doc.get("index_webcam", 0)
    ip_cam          = camera_doc.get("ip")                  # None = webcam locale
    duree_detection = camera_doc.get("duree_detection", 1200)  # défaut 20 min

    source_video = ip_cam if ip_cam else index_webcam

    # 4. IDs de la séance
    seance_id = str(seance["_id"])
    groupe_id = str(seance["groupe_id"])
    prof_id   = str(seance["prof_id"])   if seance.get("prof_id")  else ""
    salle_id  = str(seance["salle_id"])

    # 5. Marquer la séance "en_cours"
    db["seances"].update_one(
        {"_id": seance["_id"]},
        {"$set": {"status": "en_cours"}}
    )
    # Marquer la caméra "actif"
    db["cameras"].update_one(
        {"_id": camera_doc["_id"]},
        {"$set": {"actif": True}}
    )

    # 6. Ouvrir la caméra
    cap = cv2.VideoCapture(source_video)
    if not cap.isOpened():
        print(f"❌ Caméra non accessible (source: {source_video})")
        return

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    deja_identifies = set()
    debut           = time.time()
    last_api_call   = 0

    groupe = db["groupes"].find_one({"_id": seance["groupe_id"]})
    print(f"\n📷 Caméra démarrée — {NUM_SALLE}")
    print(f"   Séance  : {seance.get('matiere')} | {seance.get('heure_debut')}→{seance.get('heure_fin')}")
    print(f"   Groupe  : {groupe['nom'] if groupe else groupe_id}")
    print(f"   Durée   : {duree_detection // 60} min")
    print(f"   Source  : {'webcam ' + str(index_webcam) if not ip_cam else ip_cam}")
    print("   Appuyer Q pour quitter\n")

    # ── Boucle de détection ────────────────────────────────────────────────
    while True:
        temps_ecoule = time.time() - debut

        # Temps écoulé → fin automatique
        if temps_ecoule >= duree_detection:
            print(f"\n⏰ {duree_detection // 60} minutes écoulées — Fin de la détection.")
            break

        ret, frame = cap.read()
        if not ret:
            print("⚠️  Impossible de lire le frame.")
            break

        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        visages = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        for (x, y, w, h) in visages:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Appel API toutes les 2 secondes (optimisation)
            if time.time() - last_api_call > 2:
                last_api_call = time.time()

                visage_crop = frame[y:y+h, x:x+w]
                result = identifier_visage(visage_crop, groupe_id, prof_id, salle_id)

                if result and result.get("identifie"):
                    pid  = result["id"]
                    nom  = f"{result['nom']} {result['prenom']}"
                    type_p = result["type"]

                    couleur = (0, 255, 0) if type_p == "etudiant" else (255, 165, 0)
                    label   = f"{nom} ({'ETU' if type_p == 'etudiant' else 'PROF'})"
                    cv2.putText(frame, label, (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, couleur, 2)

                    if pid not in deja_identifies:
                        deja_identifies.add(pid)
                        enregistrer_presence(seance_id, pid, type_p)
                        print(f"✅ {label} — distance: {result.get('distance')}")
                else:
                    cv2.putText(frame, "Inconnu", (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

        # Afficher le temps restant
        restant = int(duree_detection - temps_ecoule)
        cv2.putText(frame, f"Temps restant: {restant//60:02d}:{restant%60:02d}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"Salle: {NUM_SALLE} | Detectes: {len(deja_identifies)}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)

        cv2.imshow(f"Détection — {NUM_SALLE}", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n🛑 Arrêt manuel.")
            break

    # ── Fin de détection ───────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()

    # Marquer séance terminée + caméra inactive
    db["seances"].update_one(
        {"_id": seance["_id"]},
        {"$set": {"status": "termine"}}
    )
    db["cameras"].update_one(
        {"_id": camera_doc["_id"]},
        {"$set": {"actif": False}}
    )

    print(f"\n📊 Détection terminée : {len(deja_identifies)} personne(s) identifiée(s)")
    print(f"   Génération du rapport en cours...")

    # Générer le rapport automatiquement
    try:
        r = requests.post(f"{API_URL}/rapport/{seance_id}", timeout=10)
        data = r.json()
        print(f"   ✅ Rapport généré !")
        print(f"   Présents : {data.get('nb_presents')} | Absents : {data.get('nb_absents')}")
        print(f"   Taux     : {data.get('taux_presence')}")
        print(f"   Prof présent : {'✅' if data.get('prof_present') else '❌'}")
    except Exception as e:
        print(f"   ⚠️  Erreur rapport : {e}")
        print(f"   → Lance manuellement : POST {API_URL}/rapport/{seance_id}")


if __name__ == "__main__":
    demarrer_camera()