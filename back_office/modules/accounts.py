import bcrypt
import asyncpg

from config import config as cfg
config = cfg["database"]


def verify_accounts():
    pass


def create_super_admin_account(prenom, nom, email, password):
    # Génération du hash du mot de passe
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Requêtes SQL pour insérer les données
    insert_roles = """
INSERT INTO roles (libelle) VALUES
    ('super-admin'),
    ('admin'),
    ('user');
"""

    insert_super_admin = f"""
INSERT INTO users (prenom, nom, email, password_hash, id_role, first_login)
VALUES ('{prenom}', '{nom}', '{email}', '{password_hash}', (SELECT id_role FROM roles WHERE libelle = 'super-admin'), FALSE);
"""

    # Création du fichier 'users_data.sql'
    try:
        with open("back_office/static/sql/create_super_admin_user.sql", "w") as sql_file:
            sql_file.write(insert_roles)
            sql_file.write(insert_super_admin)
        
        return True, []
    except Exception as e:
        return False, [str(e)]



async def create_user_account(prenom, nom, email, role, first_login=True, password="non défini"):
    conn = None
    try:
        # Récupération des éventuels password_hash liés à l'email de l'utilisateur
        get_email_password_hashes = f"""
        SELECT password_hash FROM users.users
        WHERE email = $1;
        """
    
        conn = await asyncpg.connect(database=config["db_name"], host=config["host"], port=config["port"], user=config["user"], password=config["password"])
        stored_password_hashes = await conn.fetch(get_email_password_hashes, email)

        # Le mot de passe à créer est-il déjà utilisé avec l'email de l'utilisateur ?
        is_unused = sum([bcrypt.checkpw(password.encode("utf-8"), stored["password_hash"].encode('utf-8')) for stored in stored_password_hashes]) == 0

        if is_unused or password == "non défini":
            # Génération du hash du mot de passe
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        
            # Requête d'ajout d'un compte utilisateur
            insert_account_query = f"""
            INSERT INTO {config["users_schema"]}.users (prenom, nom, email, password_hash, id_role, first_login)
            VALUES ($1, $2, $3, $4, (SELECT id_role FROM {config["users_schema"]}.roles WHERE libelle = $5), FALSE);
            """        
            await conn.fetchval(insert_account_query, prenom, nom, email, password_hash, role)

            return True, []
        else:
            message = ["Impossible de créer un autre compte avec ce mot de passe."]
            return False, message
    except Exception as error:
        return False, [f"Erreur lors de la création du compte : {str(error)}"]
    finally:
        if conn:
            await conn.close()

