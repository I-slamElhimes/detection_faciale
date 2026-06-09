# add_prof_email.py
# Ajoute un email à chaque professeur
from db_config import get_db

db = get_db()
profs = list(db['professeurs'].find())

print("📋 Ajout email aux professeurs :\n")
for p in profs:
    # Email généré automatiquement : prenom.nom@ecole.ma
    email = f"{p['prenom'].lower().replace(' ','-')}.{p['nom'].lower().replace(' ','-')}@ecole.ma"
    db['professeurs'].update_one(
        {'_id': p['_id']},
        {'$set': {'email': email}}
    )
    print(f"   ✅ {p['prenom']} {p['nom']} → email: {email} | password: 1234")

print("\n✅ Emails ajoutés !")
print("\n💡 Tu peux modifier les emails depuis le dashboard admin.")
print("   Ou relance ce script avec tes propres emails.")