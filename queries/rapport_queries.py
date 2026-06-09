# queries/rapport_queries.py
from db_config import get_db
from bson.objectid import ObjectId

db = get_db()

def generer_rapport_seance(seance_id):
    """
    Crée un rapport complet pour une séance :
    Liste des présents, liste des absents et statistiques.
    """
    # 1. Récupérer les infos de la séance et du groupe
    seance = db["seances"].find_one({"_id": ObjectId(seance_id)})
    if not seance:
        return {"erreur": "Séance introuvable"}

    groupe_id = seance["groupe_id"]
    
    # 2. Récupérer tous les étudiants inscrits dans ce groupe
    tous_les_etudiants = list(db["etudiants"].find({"groupe_id": groupe_id}))
    
    # 3. Récupérer les enregistrements de présence pour cette séance
    presences_docs = list(db["presences"].find({"seance_id": ObjectId(seance_id)}))
    
    # Extraire les IDs de ceux qui sont marqués "present"
    ids_presents = [str(p["personne_id"]) for p in presences_docs if p["statut"] == "present"]

    # 4. Trier les étudiants en deux listes : Présents et Absents
    liste_presents = []
    liste_absents = []

    for etu in tous_les_etudiants:
        info_etu = {
            "id": str(etu["_id"]),
            "nom": etu["nom"],
            "prenom": etu["prenom"]
        }
        if str(etu["_id"]) in ids_presents:
            liste_presents.append(info_etu)
        else:
            liste_absents.append(info_etu)

    # 5. Résumé final
    rapport = {
        "matiere": seance.get("matiere", "N/A"),
        "date": seance["date"],
        "stats": {
            "total_eleves": len(tous_les_etudiants),
            "nb_presents": len(liste_presents),
            "nb_absents": len(liste_absents),
            "taux_presence": f"{(len(liste_presents)/len(tous_les_etudiants)*100):.1f}%" if tous_les_etudiants else "0%"
        },
        "details": {
            "presents": liste_presents,
            "absents": liste_absents
        }
    }
    
    return rapport

def historique_etudiant(etudiant_id):
    """ Récupère toutes les présences et absences d'un élève précis """
    return list(db["presences"].find({"personne_id": ObjectId(etudiant_id)}))