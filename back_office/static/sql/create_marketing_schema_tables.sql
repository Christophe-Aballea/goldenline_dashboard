-- Création des tables du schema 'marketing'


-- Création table 'csp'
CREATE TABLE IF NOT EXISTS csp (
    id_csp SERIAL PRIMARY KEY,
    libelle VARCHAR(49) NOT NULL,
    csp VARCHAR(4) NOT NULL
);


-- Création table 'categories'
CREATE TABLE IF NOT EXISTS categories (
    id_categorie SERIAL PRIMARY KEY,
    libelle VARCHAR(11) NOT NULL
);


-- Création table 'clients'
CREATE TABLE IF NOT EXISTS clients (
    id_client VARCHAR(64) PRIMARY KEY,
    nb_enfants INTEGER NOT NULL DEFAULT 0,
    id_csp INTEGER NOT NULL,
    FOREIGN KEY (id_csp) REFERENCES csp (id_csp)
);


-- Création table 'collectes'
CREATE TABLE IF NOT EXISTS collectes (
    id_collecte INTEGER PRIMARY KEY,
    id_client VARCHAR(64) NOT NULL,
    date_passage DATE NOT NULL,
    FOREIGN KEY (id_client) REFERENCES clients (id_client)
);


-- Création table 'achats'
CREATE TABLE IF NOT EXISTS achats (
    id_achat SERIAL PRIMARY KEY,
    id_collecte INTEGER NOT NULL,
    id_categorie INTEGER NOT NULL,
    montant DECIMAL(7, 2) NOT NULL DEFAULT 0,
    FOREIGN KEY (id_collecte) REFERENCES collectes (id_collecte),
    FOREIGN KEY (id_categorie) REFERENCES categories (id_categorie)
);
