
CREATE TABLE IF NOT EXISTS roles (
    id_role SERIAL PRIMARY KEY,
    libelle VARCHAR(15) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id_user SERIAL PRIMARY KEY,
    nom VARCHAR(25) NOT NULL,
    prenom VARCHAR(25) NOT NULL,
    email VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    verification_code INTEGER,
    first_login BOLLEAN DEFAULT TRUE,
    id_role INTEGER NOT NULL,
    FOREIGN KEY (id_role) REFERENCES roles (id_role)
);
