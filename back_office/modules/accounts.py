import os
import bcrypt
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

def verify_accounts():
    pass

def create_super_admin_account(prenom, nom, email, password):
    # Génération du hash du mot de passe
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Requêtes SQL pour créer les tables et insérer les données
    create_roles_table = """
CREATE TABLE IF NOT EXISTS roles (
    id_role SERIAL PRIMARY KEY,
    libelle VARCHAR(15) NOT NULL UNIQUE
);
"""

    create_users_table = """
CREATE TABLE IF NOT EXISTS users (
    id_user SERIAL PRIMARY KEY,
    nom VARCHAR(25) NOT NULL,
    prenom VARCHAR(25) NOT NULL,
    email VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    id_role INTEGER NOT NULL,
    FOREIGN KEY (id_role) REFERENCES roles (id_role)
);
"""

    insert_roles = """
INSERT INTO roles (libelle) VALUES
    ('super-admin'),
    ('admin'),
    ('user');
"""

    insert_super_admin = f"""
INSERT INTO users (prenom, nom, email, password_hash, id_role)
VALUES ('{prenom}', '{nom}', '{email}', '{password_hash}', (SELECT id_role FROM roles WHERE libelle = 'super-admin'));
"""

    # Création des fichiers 'users_schema.sql' et 'users_data.sql' avec les requêtes SQL
    try:
        os.makedirs("back_office/static/sql", exist_ok=True)
        with open("back_office/static/sql/create_users_schema_tables.sql", "w") as sql_file:
            sql_file.write(create_roles_table)
            sql_file.write(create_users_table)

        with open("back_office/static/sql/populate_users_schema_tables.sql", "w") as sql_file:
            sql_file.write(insert_roles)
            sql_file.write(insert_super_admin)
        
        return True, []
    except Exception as e:
        return False, [str(e)]



def create_user_account():
    pass



def verify_credentials(credentials: HTTPBasicCredentials):
    correct_username = "admin@gl.com"
    correct_password = "password"
    if credentials.username == correct_username and credentials.password == correct_password:
        return True
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")
