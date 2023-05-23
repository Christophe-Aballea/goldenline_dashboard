# Database Goldenline

## Description

Le back-end du projet Goldenline Marketing Dashboard se compose d'une base de données PostreSQL, elle-même composée de deux schémas : 'source' et 'marketing'.

Le dossier `data` du projet contient les éléments permettant de créer et alimenter ces schémas.

## Glossaire

| Libellé | Description |
| --- | --- |
| **Client** | Un client est identifié par son nom, prénom, téléphone, email, code postal, ville, nombre d'enfants, catégorie socio-professionnelle. Est considérée comme client toute personne possédant une carte de fidélité Goldenline. Un client peut ne faire l'objet d'aucune collecte, s'il dispose d'une carte de fidélité sans avoir fait d'achat. |
| **Collecte** | Ensemble des éléments qui caractérisent un passage en caisse d'un client : identification du client, date et heure de passage, catégories des produits achetés, montant dépensé dans chaque catégorie. |
| **Categorie** | Liste des catégories de rayons chez Goldenline : DPH (Droguerie Parfumerie Hygiène), Alimentaire, Textile et Multimédia. |
| **Achat** | Un achat regroupe la catégorie et le montant dépensé dans cette catégorie lors d'un passage en caisse. Une collecte comprend au minimum 1 achat et 4 au plus. |
| **CSP** | Catégorie socio-professionnelle :<br>- Agriculteurs exploitants (AE)<br>- Artisants, commercants, chefs d'entreprise (ACCE)<br>- Cadres et professions intellectuelles supérieures (CPIS)<br>- Professions intermédiaires (PI)<br>- Employés (E)<br>- Retraités (R)<br>- Sans activité professionnelle |
| **Dépense** | Somme des montants dépensés par le ou les clients. |
| **Panier moyen** | Mesure permettant d'évaluer la valeur totale des produits achetés par un client lors d'une seule transaction.<br>Panier moyen = $\frac{\sum_{ }\text{Montants des dépenses}}{\text{Nombre de transactions}}$<br>Exemple :<br>Panier moyen Textile janvier 2023 = $\frac{\text{Montant total des ventes de la catégorie Textile en janvier 2023}}{\text{Nombre d'achats de janvier 2023 dans la catégorie Textile}}$ |


## Objectif

Forunir les données nécessaires pour générer les graphiques du site web Goldenline Marketing Dashboard :

- Dépenses :
  - par période (jour, mois, trimestre, année)
  - par catégorie (DPH, Alimentaire, Textile, Multimédia)
  - par catégorie socio-professionnelle
  - par nombre d'enfants des clients (0, 1, 2, 3, 4 et plus)
- Panier moyen :
  - par période (jour, mois, trimestre, année)
  - par catégorie (DPH, Alimentaire, Textile, Multimédia)
  - par catégorie socio-professionnelle
  - par nombre d'enfants des clients (0, 1, 2, 3, 4 et plus)

Les principes du RGPD et les recommandations de la CNIL doivent être respectés :
- Protection des données personnelles : anonymisation des données clients
- Obligation de limiter la quantités de données dès la conception : seules les données strictement nécessaires peuvent être stockées

## Fonctionnement

<p align="center"><img src="../static/img/creation_schemas.png"></p>

## Schéma 'source'

DataPro n'ayant pas accès au logiciel de caisse de Goldenline, les données clientèle récupérées via les cartes de fidélité que les clients présentent à chaque passage en caisse, sont générées de manière aléatoire dans le schéma 'source'.

<p align="center"><img src="../static/img/mcd_source.png"></p>

## Schéma 'marketing'

- Filtrage
  - Les données clients du schéma 'source' non nécessaires ne sont pas tranférées : `nom`, `prénom`, `telephone`, `email`, `code_postal`, et `ville`
  - Les périodes à analyser ne nécessitent pas de descendre jusqu'à un niveau de granularité horaire. L'attribut `date_heure_passage` (TIMESTAMP) de la table `collecte` du schéma 'source' est transformé en `date_pasage` (DATE) dans le schéma 'marketing'
- Réorganisation
  - Les données clients sont éclatées entre les tables `client` et `csp`
  - Les données catégories socio-professionnelles sont réorganisées :
    - l'attribut `csp` du schéma 'source' contenait le libellé complet, il est renommé `libelle` dans le schéma 'marketing'
    - l'attribut `csp` du schéma 'marketing' contient les initiales de la catégorie socio-professionnelle
  - Les données de collectes sont éclatées entre les tables `collecte` , `achat` et `categorie` :
    - la table `collecte` contient l'`id_client` et la date de passage `date_passage`
    - la table `achat` contient l'`id_collecte`, l'`id_categorie` et le montant de l'achat `montant`. Un achat correpond à l'ensemble des produits d'une catégorie achetés d'une collecte donnée, donc d'un passage en caisse.
    - la table `catégorie` contient le nom de chaque catégorie de produits.
- Anonymisation des données clients :
  - L'`id_client` est transformé de manière à ne pas permettre de retrouver l'`id_client` d'origine par calcul ou par comparaison après tri, grâce à la fonction de hash SHA256, native sur PostgreSQL
  - Les champs utilisés sont ceux ayant une valeur unique par client : `id_client`, `telephone`, `email` 

> _Pour des question de performance, ces opérations sont réalisées directement par le moteur de BD PostgreSQL, via une procédure stockée._

<p align="center"><img src="../static/img/mcd_marketing.png"></p>
