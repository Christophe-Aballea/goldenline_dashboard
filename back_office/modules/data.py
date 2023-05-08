import os
import psycopg2
from config import config as cf

config = cf["database"]

# Connexion base de donnée
def connect_to_db(dbname=None):
    dbname = dbname or config["db_name"]
    conn = psycopg2.connect(dbname=dbname,
                            user=config["user"],
                            password=config["password"],
                            host=config["host"],
                            port=config["port"])
    conn.autocommit = True
    cursor = conn.cursor()
    return conn, cursor


# Déconnexion base de données
def close_connection(conn, cursor):
    cursor.close()
    conn.close()


def create_database(db_name, source_schema, marketing_schema, users_schema):
    message = []
    success = True
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Création de la base de données
    try:
        # Connexion à la base de données 'postgres'
        conn, cursor = connect_to_db('postgres')

        # Vérification de l'existence de la base de données
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';")
        db_exists = cursor.fetchone()

        # Création de la base de données si elle n'existe pas
        if not db_exists:
            cursor.execute(f"CREATE DATABASE {db_name} WITH OWNER {config['user']};")
            message.append(f"Base de données {db_name} créée avec succès.")
        else:
            message.append(f"La base de données {db_name} existe déjà.")

        close_connection(conn, cursor)
    except Exception as error:
        success = False
        message.append(f"Impossible de créer {db_name}.")
        message.append(f"Erreur : {str(error)}")
        return success, message

    # Création des schemas
    try:
        # Connexion à la base de données
        conn, cursor = connect_to_db(db_name)

        create_file = {users_schema:     "create_users_schema_tables.sql",
                       source_schema:    "create_source_schema_tables.sql",
                       marketing_schema: "create_marketing_schema_tables.sql"}

        for schema in (users_schema, source_schema, marketing_schema):
            # Vérification de l'existence du schéma
            cursor.execute(f"SELECT 1 FROM information_schema.schemata WHERE schema_name = '{schema}';")
            schema_exists = cursor.fetchone()

            # Création du schéma s'il n'existe pas
            if not schema_exists:
                try:
                    cursor.execute(f"CREATE SCHEMA {schema};")
                    message.append(f"Schéma {schema} créé avec succès.")
                    # Création des tables
                    try:
                        cursor.execute(f"SET search_path TO {schema};")
                        sql_file_path = os.path.join(base_dir, "static", "sql", create_file[schema])
                        with open(sql_file_path, "r") as sql_file:
                            sql_commands = sql_file.read()
                        cursor.execute(sql_commands)
                        message.append(f"Tables du schema {schema} créées avec succès.")
                    except Exception as error:
                        success = False
                        message.append(f"Impossible de créer les tables du schéma {schema}.")
                        message.append(f"Erreur : {str(error)}")
                except Exception as error:
                    success = False
                    message.append(f"Impossible de créer le schéma {schema}.")
                    message.append(f"Erreur : {str(error)}")

            else:
                message.append(f"Le schéma {schema} existe déjà.")

        close_connection(conn, cursor)
    except Exception as error:
        success = False
        message.append("Impossible de créer les schémas.")
        message.append(f"Erreur : {str(error)}")
    return success, message


def generate_data():
    pass


def transfer_and_anonymize_data():
    pass

