# utils/auto_delete.py
from db_config import get_db
from datetime import datetime

def nettoyer_seances_terminees():
    """
    Supprime les séances de la base de données 
    si l'heure de fin est dépassée.
    """
    db = get_db()
    maintenant = datetime.now()
    date_actuelle = maintenant.strftime("%Y-%m-%d")
    heure_actuelle = maintenant.strftime("%H:%M")

    # On cherche les séances qui sont déjà finies (date passée OU heure passée)
    query = {
        "$or": [
            {"date": {"$lt": date_actuelle}}, # Date passée
            {"date": date_actuelle, "heure_fin": {"$lt": heure_actuelle}} # Même jour mais heure finie
        ]
    }

    resultat = db["seances"].delete_many(query)
    
    if resultat.deleted_count > 0:
        print(f"🧹 Nettoyage : {resultat.deleted_count} séance(s) expirée(s) supprimée(s).")
    else:
        print("✨ Aucune séance expirée à nettoyer.")

if __name__ == "__main__":
    nettoyer_seances_terminees()