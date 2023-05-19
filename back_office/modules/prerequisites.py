import psycopg2
from psycopg2.errors import InsufficientPrivilege

def check_prerequisites(host, port, user, password):
    prerequisites = True
    message = []
    try:
        # Test de la connexion à PostgreSQL
        conn = psycopg2.connect(dbname="postgres",
                                user=user,
                                password=password,
                                host=host,
                                port=port)
        cursor = conn.cursor()

        try:
            # Vérification de l'existence de l'utilisateur
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s;", (user,))
            if cursor.rowcount != 1:
                prerequisites = False

        except psycopg2.OperationalError as e:
            print(str(e))
            prerequisites = False
        except InsufficientPrivilege as e:
            print(str(e))
            prerequisites = False
        finally:
            # Fermeture des connexions
            cursor.close()
            conn.close()

    except psycopg2.OperationalError as e:
        print(str(e))
        prerequisites = False
    if prerequisites == False:
        message = ["Connexion refusée par le serveur",
                   "Causes possibles",
                   "Le serveur PostgreSQL n'est pas démarré",
                   f"L'adresse de connexion {host}:{port} n'est pas valide",
                   f"Le compte '{user}' n'existe pas",
                   f"Erreur de saisie du mot de passe du compte '{user}'",
                   f"Le compte '{user}' ne dispose pas des droits nécessaires",
                   "Accéder à la documentation"]
    return prerequisites, message
