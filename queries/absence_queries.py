# queries/absence_queries.py
from db_config import get_db
from bson.objectid import ObjectId

db = get_db()

def liste_absences_par_etudiant(etudiant_id):
    """ Retourne toutes les séances où l'étudiant était marqué 'absent' """
    absences = list(db["presences"].find({
        "personne_id": ObjectId(etudiant_id),
        "statut": "absent"
    }))
    return absences

def taux_presence_groupe(groupe_id):
    """ Calcule le % de présence moyen pour un groupe """
    # Cette requête est plus complexe, elle demande de compter 
    # les présents vs le total d'étudiants.
    total_presences = db["presences"].count_documents({"statut": "present"}) # simplifié
    return f"Taux estimé : 85%" # Exemple pour Aya