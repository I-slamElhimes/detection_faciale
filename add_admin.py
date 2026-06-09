# add_admin_only.py
from db_config import get_db

def create_admin():
    db = get_db()
    
    # 1. Préparer les données de l'admin
    # On met des infos que Aya pourra utiliser pour la page de connexion
    admin_data = {
        "login": "admin_nadir",
        "password": "password123", # À changer plus tard pour la sécurité
        "nom": "Ait-Ali",
        "prenom": "Nadir",
        "email": "nadir@ecole.com"
    }

    # 2. L'insérer dans la collection "administrateurs"
    # Si la collection n'existe pas, MongoDB la crée au moment de l'insertion
    result = db["administrateurs"].insert_one(admin_data)
    
    print(f"✅ Collection 'administrateurs' créée et activée.")
    print(f"✅ Administrateur '{admin_data['login']}' ajouté avec succès !")
    print(f"ID MongoDB : {result.inserted_id}")

if __name__ == "__main__":
    create_admin()