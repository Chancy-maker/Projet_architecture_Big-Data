# Utilisation

## 1. Arborescence attendue

```
.
├── docker-compose.yml
├── data/
│   └── kbo/                 <- décompressez ici KboOpenData_..._Full.zip
│       ├── enterprise.csv
│       ├── establishment.csv
│       ├── denomination.csv
│       ├── address.csv
│       ├── contact.csv
│       ├── activity.csv
│       ├── branch.csv
│       └── code.csv
└── notebooks/
    └── TD_construction_entreprise_bronze_final.ipynb
```

Créez les dossiers `data/kbo` et `notebooks`, décompressez-y l'archive KBO Open Data,
et placez-y le notebook.

## 2. Lancer la stack

```bash
docker compose up -d
```

Cela démarre deux services :
- **mongo** : MongoDB exposé sur `localhost:27017`.
- **jupyter** : un Jupyter (avec `pymongo` installé automatiquement au démarrage)
  exposé sur `localhost:8888`, avec le dossier `notebooks/` monté dedans.

## 3. MongoDB Compass

Connectez-vous simplement à :

```
mongodb://localhost:27017
```

Aucun utilisateur/mot de passe n'est configuré (usage local de TD). Vous verrez
apparaître la base `kbo` et ses collections au fur et à mesure que le notebook
les peuple.

## 4. Le notebook

Ouvrez `http://localhost:8888/?token=kbo`, puis le notebook dans `work/`
(monté depuis `notebooks/`). Il utilise par défaut :

- `MONGO_URI = mongodb://mongo:27017` (nom du service Docker, résolu à
  l'intérieur du réseau docker-compose)
- `DATA_DIR = /data/kbo`

Si vous préférez exécuter le notebook directement sur votre machine (hors
Docker) avec un Jupyter local, seul le service `mongo` du compose est
nécessaire ; définissez alors les variables d'environnement avant de lancer
Jupyter (ou modifiez les valeurs par défaut dans la première cellule) :

```bash
export MONGO_URI="mongodb://localhost:27017"
export MONGO_DB="kbo"
export DATA_DIR="./data/kbo"
```

## 5. Arrêter / tout réinitialiser

```bash
docker compose down          # arrête les conteneurs, garde les données Mongo
docker compose down -v       # arrête et supprime aussi le volume mongo_data
```
# Projet_architecture_Big-Data
