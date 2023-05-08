
INSERT INTO roles (libelle) VALUES
    ('super-admin'),
    ('admin'),
    ('user');

INSERT INTO users (prenom, nom, email, password_hash, id_role)
VALUES ('Christophe', 'ABALLEA', 'chr.aballea@gmail.com', '$2b$12$8lTabZy.VPqNc15lEXlKBOGly2Mf3kTkzPzvk4TtSlrc/vKL63yB.', (SELECT id_role FROM roles WHERE libelle = 'super-admin'));
