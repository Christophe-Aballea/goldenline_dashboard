import os
import datetime
import pandas as pd
import numpy as np
import psycopg2.pool
import psycopg2
import asyncio
import asyncpg

from typing import Callable

from config import config as cf


config = cf["database"]
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tasks_status = {}

def update_task_status(task_id: str, status: str):
    tasks_status[task_id] = status


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

###########################################################
#  CREATION BASE DE DONNEES - TABLES - PROCEDURE STOCKEE  #
###########################################################
def create_database(db_name, source_schema, marketing_schema, users_schema):
    global base_dir
    message = []
    success = True

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

        # Vérification de l'existence de la procédure stockée 'transfer_and_anonymization'
        try:
            cursor.execute(f"SET search_path TO {marketing_schema};")
            sql_file_path = os.path.join(base_dir, "static", "sql", "create_transfer_and_anonymization_stored_procedure.sql")
            with open(sql_file_path, "r") as sql_file:
                sql_commands = sql_file.read()
            cursor.execute(sql_commands)
            message.append("Procédure de transfert et anonymisation créée avec succès.")
        except Exception as error:
            success = False
            message.append("Impossible de créer la procédure de transfert et anonymisation.")
            message.append(f"Erreur : {str(error)}")

        close_connection(conn, cursor)
    except Exception as error:
        success = False
        message.append("Impossible de créer les schémas.")
        message.append(f"Erreur : {str(error)}")
    return success, message


#####################################################
#  GENERATION DES DONNEES ALEATOIRES SCHEMA SOURCE  #
#####################################################
def populate_source_schema_tables(customers_number, collections_number, start_date):
    global config

    source_prenoms   = os.path.join(base_dir, "static", "source", "prenom.csv")
    source_noms      = os.path.join(base_dir, "static", "source", "patronymes.csv")
    source_communes  = os.path.join(base_dir, "static", "source", "laposte_hexasmal.csv")

    # Quantités de données à générer
    nb_rows_collections = collections_number
    nb_rows_customers   = customers_number
    batch_size          = 100_000

    ##########################
    # GENERATION DES CLIENTS
    ##########################
    print("GENERATION DES CLIENTS")
    print("Préparation des données : ", end='', flush=True)
    df_client = pd.DataFrame(columns = ['id_client',
                                        'nom',
                                        'prenom',
                                        'telephone',
                                        'email',
                                        'code_postal',
                                        'ville',
                                        'csp',
                                        'nb_enfants'])

    # nom
    source = pd.read_csv(source_noms)
    noms = source[source['count'] > 100].reset_index(drop=True)
    noms_index = np.random.choice(len(noms), size=nb_rows_customers, p=(noms['count'] / noms['count'].sum()))
    df_client['nom'] = noms.iloc[noms_index]['patronyme'].values
    print("nom", end='', flush=True)

    # prenom
    source = pd.read_csv(source_prenoms)
    prenoms = source[source['sum'] > 100].reset_index(drop=True)
    prenoms_index = np.random.choice(len(prenoms), size=nb_rows_customers, p=(prenoms['sum'] / prenoms['sum'].sum()))
    df_client['prenom'] = prenoms.iloc[prenoms_index]['prenom'].values
    df_client['prenom'] = df_client['prenom'].apply(lambda x: x.capitalize())
    print(", prenom", end='', flush=True)

    # telephone
    numeros = np.random.choice(np.arange(100000000, 800000000), size=nb_rows_customers, replace=False)
    def format_phone_number(number):
        string = f"0{number}"
        return f"{string[:2]} {string[2:4]} {string[4:6]} {string[6:8]} {string[8:]}"
    df_client['telephone'] = [format_phone_number(numero) for numero in numeros]
    print(", telephone", end='', flush=True)

    # email
    choices = ["@orange.fr", "@sfr.fr", "@wanadoo.fr", "@gmail.com", "@hotmail.fr", "@hotmail.com", "@voila.fr", "@yahoo.fr"]
    providers = np.random.choice(choices, size=nb_rows_customers)
    df_client['email'] = df_client.apply(lambda row: row['prenom'][0].lower() + '.' + row['nom'].replace(' ', '').lower() + providers[row.name], axis=1)
    print(", email", end='', flush=True)

    # code postal et ville
    source = pd.read_csv(source_communes, sep=';')
    communes = source[source['code_postal'] < 97000].reset_index(drop=True)
    communes_index = np.random.randint(len(communes), size=nb_rows_customers)
    df_client['code_postal'] = communes['code_postal'][communes_index].values
    print(", code_postal", end='', flush=True)
    df_client['ville'] = communes['nom_de_la_commune'][communes_index].values
    print(", ville", end='', flush=True)

    # csp
    # Répartition (source INSEE : https://www.insee.fr/fr/statistiques/2011101?geo=METRO-1)
    # Agriculteurs exploitant                           :  0.8 %
    # Artisants, commercants, chefs d'entreprise        :  3.5 %
    # Cadres et professions intellectuelles supérieures :  9.6 %
    # Professions intermédiaires                        : 14.2 %
    # Employés                                          : 16.0 %
    # Ouvriers                                          : 12.1 %
    # Retraités                                         : 27.2 %
    # Sans activité professionnelle                     : 16.6 %
    choices = ["Agriculteurs exploitants",
               "Artisants, commercants, chefs d'entreprise",
               "Cadres et professions intellectuelles supérieures",
               "Professions intermédiaires",
               "Employés",
               "Ouvriers",
               "Retraités",
               "Sans activité professionnelle"]
    weights = [0.008, 0.035, 0.096, 0.142, 0.16, 0.121, 0.272, 0.166]
    df_client['csp'] = np.random.choice(choices, size=nb_rows_customers, p=weights)
    print(", csp", end='', flush=True)

    # nb_enfants
    # Répartition estimative
    choices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    weights = [0.22, 0.32, 0.22, 0.1, 0.035, 0.03, 0.025, 0.02, 0.015, 0.01, 0.005]
    df_client['nb_enfants'] = np.random.choice(choices, size=nb_rows_customers, p=weights)
    print(", nb_enfants", flush=True)

    # Libération des variables
    source         = None
    noms           = None
    noms_index     = None
    prenoms        = None
    prenoms_index  = None
    numeros        = None
    choices        = None
    providers      = None
    communes       = None
    communes_index = None

    # Définir la requête SQL pour insérer les données
    insert_query = '''
    INSERT INTO clients (nom, prenom, telephone, email, code_postal, ville, csp, nb_enfants)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    '''

    print("Enregistrement des données : ", end='', flush=True)

    for start_index in range(0, nb_rows_customers, batch_size):
        end_index = start_index + batch_size
        
        # Création d'un pool de connexions
        pool = psycopg2.pool.SimpleConnectionPool(1, 80,
            user=config["user"],
            password=config["password"],
            host=config["host"],
            port=config["port"],
            database=config["db_name"])
        
        # Se connecter à la base de données et insérer les données
        with pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SET search_path TO {config['source_schema']};")
                # Itérer sur chaque ligne de la dataframe et exécuter la requête d'insertion
                for row in df_client[start_index:end_index].itertuples(index=False):
                    cur.execute(insert_query, (
                        row.nom,
                        row.prenom,
                        row.telephone,
                        row.email,
                        row.code_postal,
                        row.ville,
                        row.csp,
                        row.nb_enfants
                    ))

                # Valider la transaction
                conn.commit()

        # Fermer toutes les connexions
        pool.closeall()
        print("🟩", end='', flush=True)

    print()

    # Correction des codes postaux avec un zéro de début manquant
    update_query = '''
    UPDATE clients
    SET code_postal = LPAD(code_postal, 5, '0')
    WHERE LENGTH(code_postal) < 5;
    '''

    conn, cursor = connect_to_db(config["db_name"])
    cursor.execute(f"SET search_path TO {config['source_schema']};")
    cursor.execute(update_query)
    close_connection(conn, cursor)
    print("Champ code_postal corrigé")

    # Libération mémoire
    df_client = None

    #################################
    # GENERATION DES COLLECTES
    #################################

    print("GENERATION DES COLLECTES")
    print("Préparation des données : ", end='', flush=True)

    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.date.today() - datetime.timedelta(days=1)

    # Liste de toutes les dates valides de la périodes
    dates = [single_date.date() for single_date in pd.date_range(start_date, end_date, freq='C')]

    # Génération de toutes les dates et heures
    # Choix aléatoire de nb_rows_collections dans la liste des dates valides
    # Génération aléatoire de nb_rows_collections heure / minutes / secondes entre 9h00 et 20h59 (horaires d'ouverture)
    dates_array = np.random.choice(dates, size=nb_rows_collections)
    hours       = np.random.randint(9, 21, size=nb_rows_collections)
    minutes     = np.random.randint(0, 60, size=nb_rows_collections)
    seconds     = np.random.randint(0, 60, size=nb_rows_collections)

    # Création des timestamp
    all_dates_heures = [
        datetime.datetime.combine(dates_array[i], datetime.time(hours[i], minutes[i], seconds[i])).strftime('%Y-%m-%d %H:%M:%S')
        for i in range(nb_rows_collections)
    ]

    # Tri all_dates_heures en ordre croissant
    # Pour simuler l'ordre chrnologique des collectes
    all_dates_heures.sort()
    print("date_heure_passage", end='', flush=True)


    # Génération aléatoire de nb_rows_collections id_client parmi nb_rows_customers
    #all_id_clients = np.random.randint(1, nb_rows_customers + 1, size=nb_rows_collections)
    all_id_clients = np.random.choice(np.arange(1, nb_rows_customers + 1), size=nb_rows_collections, replace=True)
    print(", id_client")


    # Création des collectes et enregistrement en BD par lots de taille batch_size
    batch_number = 0
    print("Génération des montants et enegistrement des données : ", end='', flush=True)

    while nb_rows_collections:
        # Info du lot
        nb_rows = min(batch_size, nb_rows_collections)
        start_index = batch_size * batch_number
        end_index = start_index + nb_rows
        dates_heures = all_dates_heures[start_index:end_index]
        id_clients = all_id_clients[start_index:end_index]

        # Définition des paramètres du montant total d'une collecte
        # Distribution selon une loi normale de moyenne 75 €, écart-type de 45 €
        min_value = 0
        mean = 75
        std_dev = 45

        # Liste vide pour stocker les données
        data = []

        # Boucler sur chaque entier de 1 à batch_size pour créer chaque ligne de la dataframe
        for id_collecte in range(1, nb_rows + 1):
            # Tirage au sort d'un montant total aléatoire, suivant une loi de distribution normale
            # avec un minimum de 1.5, on suppose qu'aucun article ne coûte moins de 1.5 € chez Goldenline
            total = max(abs(np.random.normal(loc=mean, scale=std_dev)), 1.5)

            # Tirage au sort du nombre de catégories à renseigner
            # On suppose que :
            # 35 % du temps une collecte correspond à 2 catégories
            # 30 % du temps à 3 catégories
            # 20 % du temps à 1 catégorie
            # 15 % du temps aux 4 catégories
            nb_category = np.random.choice([1, 2, 3, 4], p=[0.2, 0.35, 0.3, 0.15])

            # Tirage au sort des catégories à renseigner
            choices = [0, 1, 2, 3]
            weights = [0.1, 0.35, 0.35, 0.2]
            categories = np.random.choice(choices, size=nb_category, p=weights, replace=False)

            # Répartition aléatoire du total dans les catégories
            alpha = np.ones(nb_category)
            percents = np.random.dirichlet(alpha, size=1)
            montants = [0, 0, 0, 0]
            for i, c in enumerate(categories):
                montants[c] = max(total * percents[0][i], 1.5)

            # Création d'une ligne de données
            row = {
                'date_heure_passage': dates_heures[id_collecte - 1],
                'montant_dph': montants[0],
                'montant_alimentaire': montants[1],
                'montant_textile': montants[2],
                'montant_multimedia': montants[3],
                'id_client': id_clients[id_collecte - 1]
            }

            # Ajout de la ligne de données générée
            data.append(row)

        # Création d'une dataframe à partir de la liste de données
        df_collecte = pd.DataFrame(data)

        # Arrondi de tous les montants à 2 chiffres après la virgule
        df_collecte = df_collecte.round({'montant_dph': 2, 'montant_alimentaire': 2, 'montant_textile': 2, 'montant_multimedia': 2})

        # Création d'un pool de connexions
        pool = psycopg2.pool.SimpleConnectionPool(1, 80,
            user=config["user"],
            password=config["password"],
            host=config["host"],
            port=config["port"],
            database=config["db_name"])
        
        # Requête SQL d'insertion des données
        insert_query = '''
        INSERT INTO collectes (date_heure_passage, montant_dph, montant_alimentaire, montant_textile, montant_multimedia, id_client)
        VALUES (%s, %s, %s, %s, %s, %s)
        '''

        # Connection à la base de données et insértion des données
        with pool.getconn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SET search_path TO {config['source_schema']};")
                # Itérer sur chaque ligne de la dataframe et exécuter la requête d'insertion
                for row in df_collecte.itertuples(index=False):
                    cur.execute(insert_query, (
                        row.date_heure_passage,
                        row.montant_dph,
                        row.montant_alimentaire,
                        row.montant_textile,
                        row.montant_multimedia,
                        row.id_client
                    ))

                # Valider la transaction
                conn.commit()

        # Fermeture des connexions
        pool.closeall()

        nb_rows_collections -= nb_rows
        batch_number += 1
        print("🟩", end='', flush=True)

    print()


######################################
#  TABLES STATIQUE SCHEMA MARKETING  #
######################################
def populate_marketing_schema_static_tables():

    # Contenu de la table 'csp'
    libelles_csp = ["Agriculteurs exploitants",
                    "Artisants, commercants, chefs d'entreprise",
                    "Cadres et professions intellectuelles supérieures",
                    "Professions intermédiaires",
                    "Employés",
                    "Ouvriers",
                    "Retraités",
                    "Sans activité professionnelle"]
    
    # Initiales pour le champ 'csp'
    def get_initials(libelle):
        words = libelle.split()
        initials = ''.join([word[0] for word in words if len(word) > 2]).upper()
        return initials
    
    conn, cursor = connect_to_db(config["db_name"])
    cursor.execute(f"SET search_path TO {config['marketing_schema']};")
    
    # Remplissage 'sc_marketing'.csps
    for libelle in libelles_csp:
        csp = get_initials(libelle)
        cursor.execute("INSERT INTO csp (libelle, csp) VALUES (%s, %s)", (libelle, csp))

    # Remplissage 'sc_marketing'.categories
    for libelle in ["DPH", "Alimentaire", "Textile", "Multimedia"]:     
        cursor.execute("INSERT INTO categories (libelle) VALUES (%s)", (libelle, ))  
    
    close_connection(conn, cursor)


##########################################################################
#  TRANSFERT SCHEMA SOURCE -> ANONYMISATION CLIENTS -> SCHEMA MARKETING  #
##########################################################################
def transfer_and_anonymize_data():
    conn, cursor = connect_to_db(config["db_name"])
    cursor.execute(f"SET search_path TO {config['marketing_schema']};")
    
    sql = """
        CALL {schema}.transfer_data_and_anonymize(%s, %s);
    """.format(schema=config["marketing_schema"])
    cursor.execute(sql, (config["source_schema"], config["marketing_schema"]))

    close_connection(conn, cursor)

# Enregistrement du compte super-admin dans le schéma 'users'
def create_super_user_admin():
    try:
        conn, cursor = connect_to_db(config["db_name"])
        cursor.execute(f"SET search_path TO {config['users_schema']};")
        sql_file_path = os.path.join(base_dir, "static", "sql", "create_super_admin_user.sql")
        with open(sql_file_path, "r") as sql_file:
            sql_commands = sql_file.read()
        cursor.execute(sql_commands)
        close_connection(conn, cursor)

        if os.path.exists(sql_file_path):
            os.remove(sql_file_path)

    except Exception as error:
        pass

# Calcul du nombre de lignes ayant dû être générées
async def get_total_rows(db_name, host, port, user, password, marketing_schema, users_schema):
    query = f"""
    SELECT (
        (SELECT COUNT(*) FROM {marketing_schema}.clients) +
        (SELECT COUNT(*) FROM {marketing_schema}.collectes) +
        (SELECT COUNT(*) FROM {users_schema}.users)
    ) AS total_rows;
    """
    
    conn = await asyncpg.connect(database=db_name, host=host, port=port, user=user, password=password)
    
    result = await conn.fetchrow(query)
    await conn.close()

    return result["total_rows"]


##########################################################################
#  TRANSFERT SCHEMA SOURCE -> ANONYMISATION CLIENTS -> SCHEMA MARKETING  #
#  ENREGISTREMENT COMPTE SUPER-ADMIN SCHEMA USERS                        #
##########################################################################
async def generate_data(task_id, customer_number, collections_number, start_date, update_status_callback: Callable[[str, str], None]):
    update_status_callback(task_id, "running")
    try:
        # Remplissage aléatoire schema source
        populate_source_schema_tables(customer_number, collections_number, start_date)

        # Tables statiques
        populate_marketing_schema_static_tables()

        # Transfert source_schema -> anonymisation -> marketing_shema
        transfer_and_anonymize_data()
        print("Données clients anonymisées et transfert effectué")

        # Enregistrement du compte super-admin et suppression des traces
        create_super_user_admin()
        print("Compte super-admin créé avec succès")

        # Vérification du transfert
        total_expected = customer_number + collections_number + 1
        print(f"Nombre d'enregistrements attendus : {total_expected:,}".replace(",", " "))
        total_rows = await get_total_rows(config["db_name"], config["host"], config["port"], config["user"], config["password"], config['marketing_schema'], config["users_schema"])
        print(f"Nombre d'enregistrements trouvés  : {total_rows:,}".replace(",", " "))

        if total_expected == total_rows:
            update_status_callback(task_id, "completed")
        else:
            update_task_status(task_id, "failed")    

    except Exception as error:
        update_task_status(task_id, "failed")

