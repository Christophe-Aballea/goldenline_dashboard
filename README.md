# Goldenline Marketing Dashboard

Le Goldenline Marketing Dashboard est un projet Python qui fournit un site web permettant au service marketing de Goldenline d'analyser les données clientèle sous forme de graphiques interactifs et faciles à comprendre.

## Table des matières

- [Goldenline Marketing Dashboard](#goldenline-marketing-dashboard)
  - [Table des matières](#table-des-matières)
  - [Introduction](#introduction)
  - [Fonctionnalités](#fonctionnalités)
  - [Technologies utilisées](#technologies-utilisées)
  - [Installation et prérequis](#installation-et-prérequis)
    - [Prérequis](#prérequis)
    - [Installation](#installation)
  - [Utilisation](#utilisation)

## Introduction

Ce projet a pour objectif de fournir un outil d'analyse de données pour le service marketing de Goldenline. Les utilisateurs pourront explorer et analyser les données clientèle à l'aide de divers graphiques interactifs, permettant ainsi d'améliorer la prise de décisions et l'efficacité des campagnes marketing.

## Fonctionnalités

- Visualisation des données clientèle
- Filtrage des données par période, catégories de produits, catégories socio-professionnelles, nombre d'enfants
- Export des données
- Interface utilisateur intuitive et adaptative

## Technologies utilisées

- Python
- Flask (Framework Web)
- Pandas (Bibliothèque de manipulation et d'analyse de données)
- PostgreSQL (SGBD/R)

## Installation et prérequis

### Prérequis

- Avoir un serveur PostgreSQL installé et démarré
  
  Exemple d'installation sur Linux Ubuntu (source : https://www.postgresql.org/download/linux/ubuntu/) :
  ``` bash
  $ sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
  $ wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
  $ sudo apt-get update
  ```
  
  Démarrage :
  ``` bash
  $ sudo service postgresql start
   * Starting PostgreSQL 15 database server
  ```
- Avoir créé un utilisateur d'application
  
  Création d'un utilisateur :
  ``` bash
  $ sudo -u postgres psql
  psql (15.2 (Ubuntu 15.2-1.pgdg22.04+1))
  Type "help" for help.
  ```
  ``` sql
  postgres=# CREATE USER nom_utilisteur_d_application PASSWORD 'mot_de_passe_fort' CREATEDB;
  CREATE ROLE
  postgres=# \q
  ```

- Disposer de l'adresse IP du serveur (127.0.0.1 par défaut), du port d'écoute (5432 par défaut) et des identifiants de connexion de l'utilisateur d'application

### Installation

- Cloner le dépôt :
  ``` bash
  $ git clone https://github.com/Christophe-Aballea/goldenline
  ```
- Installer les dépendances du projet :
  ``` bash
  $ cd goldenline
  $ pip install -r requirements.txt
  ```
- Exécuter le projet en local
  ``` bash
  $ flask --app goldenline-be:back run
  ```

## Utilisation

Le terminal dans lequel la commande `flask` a été excécutée doit afficher le lien à ouvrir dans un navigateur. Exemple : `* Running on http://127.0.0.1:5000`.  

<p align="center"><img src="./static/img/mep0.png" width="307" height="664"></p>  
Au premier lancement le système vérifie le statut du projet et propose sa mise en production.  

<p align="center"><img src="./static/img/mep1.png" width="307" height="664"></p>  
La première étape consiste à vérifier la connectivité au serveur PostgreSQL et l'existence d'un utilisateur d'application avec les droits suffisants.  

<p align="center"><img src="./static/img/mep2.png" width="307" height="664"></p>  
Lorsque les paramètres saisis sont correct, l'écran suivant propose le paramétrage des noms de base de données et schémas, ainsi que le nombre de clients et de collectes à générer. Attention, la mise en production avec le paramétrage de base (3 000 000 de clients / 40 000 000 de collectes) prend un temps certain. Sur une machine équipée de 64 Go de RAM et un processeur Core i9-9900 K 16 coeurs, 3 h 22 min ont été nécessaires.
