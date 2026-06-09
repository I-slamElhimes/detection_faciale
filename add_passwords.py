# add_passwords.py
from db_config import get_db

db = get_db()

r1 = db['professeurs'].update_many({'password': {'$exists': False}}, {'$set': {'password': '1234'}})
r2 = db['etudiants'].update_many({'password': {'$exists': False}}, {'$set': {'password': '1234'}})

print(f"✅ Professeurs mis à jour : {r1.modified_count}")
print(f"✅ Étudiants mis à jour   : {r2.modified_count}")
print("\n📋 Identifiants de connexion :")
print("   Admin      → username: admin      | password: admin123")
print("   Admin      → username: admin_nadir| password: password123")
print("   Professeur → CNE ou email         | password: 1234")
print("   Étudiant   → CNE (ex: E100001)    | password: 1234")