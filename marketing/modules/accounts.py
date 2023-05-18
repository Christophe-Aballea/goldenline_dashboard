import bcrypt

from back_office.modules.db_utils import create_connection
from config import get_users_schema


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
