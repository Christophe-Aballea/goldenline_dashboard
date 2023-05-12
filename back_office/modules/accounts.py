import bcrypt
from random import choice

from back_office.modules.db_utils import create_connection
from back_office.modules.authentication import get_verification_code
from config import get_users_schema


async def list_of_existing_accounts():
    users_schema = get_users_schema()
    conn = None
    try:
        conn = await create_connection()

        # Roles existants
        get_roles_query = f"""
        SELECT libelle
        FROM {users_schema}.roles
        ORDER BY id_role;
        """
        roles = await conn.fetch(get_roles_query)
        existing_accounts = {role["libelle"]:[] for role in roles}

        # Comptes existants
        get_accounts_query = f"""
        SELECT email, libelle AS role
        FROM {users_schema}.users u
        JOIN {users_schema}.roles r ON u.id_role = r.id_role
        ORDER BY u.id_user;
        """

        accounts = await conn.fetch(get_accounts_query)
        for account in accounts:
            existing_accounts[account["role"]].append(account["email"])

        return True, existing_accounts
    except Exception as error:
        return False, [f"Erreur : ", str(error)]
    finally:
        if conn:
            await conn.close()

async def verify_numbers_of_accounts():
    users_schema = get_users_schema()
    conn = None
    try:
        conn = await create_connection()

        # Nombres de comptes pour chaque rôle
        get_numbers_of_accounts_query = f"""
        SELECT  (SELECT COUNT(*) FROM {users_schema}.users u LEFT JOIN {users_schema}.roles r ON u.id_role = r.id_role WHERE r.libelle = 'superadmin') AS superadmin,
                (SELECT COUNT(*) FROM {users_schema}.users u LEFT JOIN {users_schema}.roles r ON u.id_role = r.id_role WHERE r.libelle = 'admin') AS admin,
                (SELECT COUNT(*) FROM {users_schema}.users u LEFT JOIN {users_schema}.roles r ON u.id_role = r.id_role WHERE r.libelle = 'user') AS user;
        """
        account_numbers = await conn.fetchrow(get_numbers_of_accounts_query)

        # Succès si au moins 1 compte admin / superadmin et au moin un compte user
        success = (account_numbers["superadmin"] + account_numbers["admin"]) > 0 and account_numbers["user"] > 0

        _, accounts = await list_of_existing_accounts()

        return success, accounts
    except Exception as error:
        return False, [f"Erreur : ", str(error)]
    finally:
        if conn:
            await conn.close()


def create_superadmin_account(prenom, nom, email, password):
    # Génération du hash du mot de passe
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Requêtes SQL pour insérer les données
    insert_roles = """
INSERT INTO roles (libelle) VALUES
    ('superadmin'),
    ('admin'),
    ('user');
"""

    insert_superadmin = f"""
INSERT INTO users (prenom, nom, email, password_hash, id_role, first_login)
VALUES ('{prenom}', '{nom}', '{email}', '{password_hash}', (SELECT id_role FROM roles WHERE libelle = 'superadmin'), FALSE);
"""

    # Création du fichier 'create_superadmin_user.sql'
    try:
        with open("back_office/static/sql/create_superadmin_user.sql", "w") as sql_file:
            sql_file.write(insert_roles)
            sql_file.write(insert_superadmin)
        
        return True, []
    except Exception as e:
        return False, [str(e)]



async def create_user_account(prenom, nom, email, role, verification_code=None, first_login=True, password="non défini"):
    users_schema = get_users_schema()
    conn = None
    success = True
    message = []
    try:
        # Récupération des éventuels password_hash liés à l'email de l'utilisateur
        get_email_password_hashes_query = f"""
        SELECT password_hash FROM {users_schema}.users
        WHERE email = $1;
        """
    
        conn = await create_connection()
        stored_password_hashes = await conn.fetch(get_email_password_hashes_query, email)

        # Le mot de passe à créer est-il déjà utilisé avec l'email de l'utilisateur ?
        is_unused = sum([bcrypt.checkpw(password.encode("utf-8"), stored["password_hash"].encode('utf-8')) for stored in stored_password_hashes]) == 0

        # L'identifiant est-il déjà utilisé pour un autre compte avec un rôle identique ?
        is_email_used_with_same_role_query = f"""
        SELECT COUNT(*) AS account_count
        FROM {users_schema}.users
        WHERE email = $1 AND id_role = (SELECT id_role FROM {users_schema}.roles WHERE libelle = $2);
        """

        # L'email est-il déjà utilisé avec le même rôle ?
        same_account_type_count = await conn.fetchrow(is_email_used_with_same_role_query, email, role)
        if same_account_type_count["account_count"] > 0:
            success = False
            message.append(f"Création de plusieurs comptes avec le même identifiant et le même rôle non autorisée.")
            return success, message

        if is_unused or password == "non défini":
            # Génération du hash du mot de passe
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            if not verification_code:
                verification_code = get_verification_code()

            # Requête d'ajout d'un compte utilisateur
            insert_account_query = f"""
            INSERT INTO {users_schema}.users (prenom, nom, email, password_hash, verification_code, id_role, first_login)
            VALUES ($1, $2, $3, $4, $5, (SELECT id_role FROM {users_schema}.roles WHERE libelle = $6), $7);
            """

            try:    
                await conn.fetchval(insert_account_query, prenom, nom, email, password_hash, int(verification_code), role, first_login)
                message.append(f"Compte {email} / {verification_code} créé avec succès")
            except Exception as error:
                message.append(f"Erreur à la création du compte : {str(error)}")
                success = False
            return success, message
        else:
            message.append("Impossible de créer un autre compte avec ce mot de passe.")
            return False, message
    except Exception as error:
        print(f"Erreur : {str(error)}")
        message.append((f"Erreur lors de la création du compte : {str(error)}"))
        return False, message
    finally:
        if conn:
            await conn.close()
