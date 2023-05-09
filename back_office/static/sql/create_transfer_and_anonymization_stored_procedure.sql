
-- Création table 'last_execution'
CREATE TABLE IF NOT EXISTS last_execution(
    id SERIAL PRIMARY KEY,
    executed_at TIMESTAMP NOT NULL
);


-- Fonction de hash pour anonymisation données clients
CREATE OR REPLACE FUNCTION hash_client_data(p_id_client INTEGER, p_email VARCHAR, p_telephone VARCHAR)
RETURNS VARCHAR(64) AS $$
DECLARE
    v_hash VARCHAR(64);
BEGIN
    SELECT encode(sha256(concat(p_id_client::TEXT, p_email, p_telephone)::bytea), 'hex')
    INTO v_hash;
    RETURN v_hash;
END;
$$ LANGUAGE plpgsql;


-- Procédure stockée 'transfer_and_anonymization'
CREATE OR REPLACE PROCEDURE transfer_data_and_anonymize(source_schema TEXT, marketing_schema TEXT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_id_csp_mapping INTEGER;
    v_last_execution TIMESTAMP;
    v_sql TEXT;
BEGIN
    -- Récupération de la date de la dernière exécution
    EXECUTE format('
        SELECT executed_at FROM %I.last_execution ORDER BY id DESC LIMIT 1;
    ', marketing_schema) INTO v_last_execution;

    -- Transfert des données de la table clients
    EXECUTE format('
        INSERT INTO %I.clients (id_client, nb_enfants, id_csp)
        SELECT 
            %I.hash_client_data(c.id_client, c.email, c.telephone),
            c.nb_enfants,
            %I.csp.id_csp
        FROM %I.clients AS c
        JOIN %I.csp ON c.csp = %I.csp.libelle
        WHERE (%L IS NULL) OR (%I.hash_client_data(c.id_client, c.email, c.telephone) > (SELECT COALESCE(MAX(id_client), %L) FROM %I.clients));
    ', marketing_schema, marketing_schema, marketing_schema, source_schema, marketing_schema, marketing_schema, v_last_execution, marketing_schema, '', marketing_schema);

    -- Transfert des données de la table collectes
    EXECUTE format('
        INSERT INTO %I.collectes (id_collecte, id_client, date_passage)
        SELECT 
            col.id_collecte,
            %I.hash_client_data(c.id_client, c.email, c.telephone),
            col.date_heure_passage::DATE
        FROM %I.collectes AS col
        JOIN %I.clients AS c ON col.id_client = c.id_client
        WHERE (%L IS NULL) OR (col.date_heure_passage > %L) AND (%I.hash_client_data(c.id_client, c.email, c.telephone) NOT IN (SELECT id_client FROM %I.clients));
    ', marketing_schema, marketing_schema, source_schema, source_schema, v_last_execution, v_last_execution, marketing_schema, marketing_schema);

    -- Transfert des données vers la table achats pour chaque catégorie
    FOR v_id_csp_mapping IN 1..4 LOOP
        v_sql := format('
            INSERT INTO %I.achats (id_collecte, id_categorie, montant)
            SELECT 
                col.id_collecte,
                %L::INTEGER,
                CASE %L::INTEGER
                    WHEN 1 THEN col.montant_dph
                    WHEN 2 THEN col.montant_alimentaire
                    WHEN 3 THEN col.montant_textile
                    WHEN 4 THEN col.montant_multimedia
                END
            FROM %I.collectes AS col
            WHERE 
                ((%L IS NULL) OR (col.date_heure_passage > %L)) AND
                CASE %L::INTEGER
                    WHEN 1 THEN col.montant_dph
                    WHEN 2 THEN col.montant_alimentaire
                    WHEN 3 THEN col.montant_textile
                    WHEN 4 THEN col.montant_multimedia
                END > 0;
        ', marketing_schema, v_id_csp_mapping, v_id_csp_mapping, source_schema, v_last_execution, v_last_execution, v_id_csp_mapping);
        EXECUTE v_sql;
    END LOOP;

    -- Enregistrement de la date d'exécution actuelle
    EXECUTE format('
        INSERT INTO %I.last_execution (executed_at) VALUES (NOW());
    ', marketing_schema);
END;
$$;
