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
        return False, [f"Erreur lors de la tentative de récupération des comptes existants : {str(error)}"]
    finally:
        if conn:
            await conn.close()


def can_be_put_into_production(accounts):
    admin_accounts = len(accounts.get("superadmin", [])) + len(accounts.get("admin", []))
    user_accounts = len(accounts.get("user", []))
    return admin_accounts > 0 and user_accounts > 0


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
            message.append(f"Création de plusieurs comptes avec le même identifiant non autorisée.")
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
                message.append(f"{role.capitalize()} {email} ({verification_code}) créé avec succès")
            except Exception as error:
                message.append(f"Erreur lors de la création du compte : {str(error)}")
                success = False
            return success, message
        else:
            message.append("Impossible de créer un autre compte avec ce mot de passe.")
            return False, message
    except Exception as error:
        message.append((f"Erreur lors de la création du compte : {str(error)}"))
        return False, message
    finally:
        if conn:
            await conn.close()

# Lister les comptes de niveau(x) inférieur(s)
async def get_users_by_roles(current_user_id_role):
    users_schema = get_users_schema()
    message = []
    conn = None
    try:
        get_users_accounts_query = f"""
        SELECT nom, prenom, email, libelle as role, verification_code
        FROM {users_schema}.users u
        LEFT JOIN {users_schema}.roles r
        ON u.id_role = r.id_role
        WHERE u.id_role > {current_user_id_role}
        ORDER BY nom, prenom;
        """
        conn = await create_connection()
        message = await conn.fetch(get_users_accounts_query)
        success = True
    except Exception as error:
        message.append((f"Immpossible de récupérer la liste des comptes : {str(error)}"))
        success = False
    finally:
        if conn:
            await conn.close()
       
    return success, message

# Récupération des informations d'un compte en fonction de l'email
async def get_login_type_from_email(email):
    users_schema = get_users_schema()
    message = []
    conn = None
    try:
        get_user_infos_query = f"""
        SELECT id_user, email, password_hash, id_role, first_login, verification_code
        FROM {users_schema}.users
        WHERE email = '{email}';
        """
        conn = await create_connection()
        user = await conn.fetchrow(get_user_infos_query)

        if user is None:
            success = False
            message.append("Identifiant, mot de passe ou code d'activation incorrect")
        else:
            success = True
            message  = user["first_login"]
    except Exception as error:
        success = False
        message.append(f"Impossible de vérifier la validité des informations de connexion : {str(error)}")
    finally:
        if conn:
            await conn.close()
       
    return success, message


# Activation d'un compte
# - suppression du code d'activation
# - 'first_login' -> False
# - hashage et enregistrement du password
async def activate_user(email, password):
    users_schema = get_users_schema()
    message = []
    success = False
    conn = None
    try:
        # Hashage du password
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Requête d'activation de l'utilisateur
        activate_user_update_query = f"""
        UPDATE {users_schema}.users
        SET (password_hash, verification_code, first_login) = ('{password_hash}', NULL, false)
        WHERE email = '{email}';
        """
        conn = await create_connection()
        result = await conn.execute(activate_user_update_query)

        if result:
            success = True
            message.append(f"Compte {email} activé avec succès")
        else:
            success = False
            message.append(f"Impossible d'activer le compte {email}")
    except Exception as error:
        message.append(f"Erreur : {str(error)}")
    finally:
        if conn:
            await conn.close()
    return success, message
