-- Création des tables du schéma 'source'


-- Création table 'clients'
CREATE TABLE IF NOT EXISTS clients (
    id_client SERIAL PRIMARY KEY,
    nom VARCHAR(60) NOT NULL,
    prenom VARCHAR(25) NOT NULL,
    telephone VARCHAR(14),
    email VARCHAR(63),
    code_postal VARCHAR(5) NOT NULL,
    ville VARCHAR(40) NOT NULL,
    csp VARCHAR(49) NOT NULL,
    nb_enfants INTEGER NOT NULL DEFAULT 0
);


-- Création table 'collecte'
CREATE TABLE IF NOT EXISTS collectes (
    id_collecte SERIAL PRIMARY KEY,
    date_heure_passage TIMESTAMP NOT NULL,
    montant_dph DECIMAL(7,2) NOT NULL DEFAULT 0,
    montant_alimentaire DECIMAL(7,2) NOT NULL DEFAULT 0,
    montant_textile DECIMAL(7,2) NOT NULL DEFAULT 0,
    montant_multimedia DECIMAL(7,2) NOT NULL DEFAULT 0,
    id_client INTEGER NOT NULL,
    FOREIGN KEY (id_client) REFERENCES clients (id_client)
);
