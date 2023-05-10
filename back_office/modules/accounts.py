import bcrypt
from random import choice

from back_office.modules.db_utils import create_connection, users_schema


async def verify_accounts():
    conn = None
    try:
        message = {}

        # Nombre de comptes super-admin, admin et user
        get_accounts_query = f"""
        SELECT email, libelle AS role
        FROM {users_schema}.users u
        JOIN {users_schema}.roles r ON u.id_role = r.id_role
        ORDER BY u.id_role;
        """

        conn = await create_connection()
        accounts = await conn.fetch(get_accounts_query)

        for account in accounts:
            if account["role"] in message:
                message[account["role"]].append(account["email"])
            else:
                message[account["role"]] = [account["email"]]

        print(message)
        return True, message
    except Exception as error:
        return False, [f"Erreur : ", str(error)]
    finally:
        if conn:
            await conn.close()


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

    # Création du fichier 'create_super_admin_user.sql'
    try:
        with open("back_office/static/sql/create_super_admin_user.sql", "w") as sql_file:
            sql_file.write(insert_roles)
            sql_file.write(insert_super_admin)
        
        return True, []
    except Exception as e:
        return False, [str(e)]



async def create_user_account(prenom, nom, email, role, verification_code=None, first_login=True, password="non défini"):
    conn = None
    try:
        # Récupération des éventuels password_hash liés à l'email de l'utilisateur
        get_email_password_hashes = f"""
        SELECT password_hash FROM users.users
        WHERE email = $1;
        """
    
        conn = await create_connection()
        stored_password_hashes = await conn.fetch(get_email_password_hashes, email)

        # Le mot de passe à créer est-il déjà utilisé avec l'email de l'utilisateur ?
        is_unused = sum([bcrypt.checkpw(password.encode("utf-8"), stored["password_hash"].encode('utf-8')) for stored in stored_password_hashes]) == 0

        if is_unused or password == "non défini":
            # Génération du hash du mot de passe
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            if not verification_code:
                # Génération d'un code de vérification aléatoire
                verification_code = [str(choice(range(1, 10)))]

                while len(verification_code) != 4:
                    digit = str(choice(range(10)))
                    if digit not in verification_code:
                        verification_code.append(digit)

            # Requête d'ajout d'un compte utilisateur
            insert_account_query = f"""
            INSERT INTO {users_schema}.users (prenom, nom, email, password_hash, verification_code, first_login, id_role)
            VALUES ($1, $2, $3, $4, $5, (SELECT id_role FROM {users_schema}.roles WHERE libelle = $6), $7);
            """        
            await conn.fetchval(insert_account_query, prenom, nom, email, password_hash, int(verification_code), role, first_login)

            return True, []
        else:
            message = ["Impossible de créer un autre compte avec ce mot de passe."]
            return False, message
    except Exception as error:
        return False, [f"Erreur lors de la création du compte : {str(error)}"]
    finally:
        if conn:
            await conn.close()
