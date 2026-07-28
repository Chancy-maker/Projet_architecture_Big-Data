import csv
import os
from pathlib import Path

import pymongo

DATA_DIR   = Path(os.getenv("KBO_DATA_DIR", "/home/jovyan/work/data/KBO"))
MONGO_URI  = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
DB_NAME    = os.getenv("MONGO_DB", "bce_db")
BATCH_SIZE = 10_000

FILES_TO_COLLECTIONS = {
    "enterprise.csv":    "kbo_enterprise",
    "establishment.csv": "kbo_establishment",
    "branch.csv":        "kbo_branch",
    "denomination.csv":  "kbo_denomination",
    "address.csv":       "kbo_address",
    "contact.csv":       "kbo_contact",
    "activity.csv":      "kbo_activity",
    "code.csv":          "kbo_code",
}


def get_db():
    client = pymongo.MongoClient(MONGO_URI)
    return client[DB_NAME]

def load_csv_to_collection(db, csv_path: Path, collection_name: str, batch_size: int = BATCH_SIZE):
    """Insere un CSV dans sa collection par lots, en streaming (csv.DictReader
    est un generateur -- on ne charge jamais tout le fichier en memoire, quelle
    que soit sa taille)."""
    col = db[collection_name]
    col.drop() 

    batch = []
    total = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            batch.append(row)
            if len(batch) >= batch_size:
                col.insert_many(batch, ordered=False)
                total += len(batch)
                print(f"  [{collection_name}] {total:,} lignes inserees...")
                batch = []
        if batch:
            col.insert_many(batch, ordered=False)
            total += len(batch)

    print(f"[{collection_name}] termine : {total:,} lignes")
    return total


def load_all(db):
    print(f"Chargement depuis {DATA_DIR}")
    for filename, collection_name in FILES_TO_COLLECTIONS.items():
        csv_path = DATA_DIR / filename
        if not csv_path.exists():
            raise FileNotFoundError(
                f"{csv_path} introuvable -- verifiez que le volume KBO est bien monte "
                f"sur ce service (voir le commentaire en tete de fichier)."
            )
        load_csv_to_collection(db, csv_path, collection_name)

def create_indexes(db):
    db.kbo_enterprise.create_index("EnterpriseNumber", unique=True)
    db.kbo_establishment.create_index("EnterpriseNumber")
    db.kbo_establishment.create_index("EstablishmentNumber")
    db.kbo_branch.create_index("EnterpriseNumber")
    db.kbo_branch.create_index("Id")
    db.kbo_denomination.create_index("EntityNumber")
    db.kbo_address.create_index("EntityNumber")
    db.kbo_contact.create_index("EntityNumber")
    db.kbo_activity.create_index("EntityNumber")
    print("index crees")

def _detail_lookups(primary_key: str) -> list:
    """Les 4 $lookup partages par le niveau entreprise, etablissement et
    succursale -- seul local_field change (EnterpriseNumber / EstablishmentNumber / Id)."""
    return [
        {"$lookup": {"from": "kbo_denomination", "localField": primary_key,
                      "foreignField": "EntityNumber", "as": "denominations"}},
        {"$lookup": {"from": "kbo_address", "localField": primary_key,
                      "foreignField": "EntityNumber", "as": "addresses"}},
        {"$lookup": {"from": "kbo_contact", "localField": primary_key,
                      "foreignField": "EntityNumber", "as": "contacts"}},
        {"$lookup": {"from": "kbo_activity", "localField": primary_key,
                      "foreignField": "EntityNumber", "as": "activities"}},
    ]


def _establishments_lookup() -> dict:
    return {
        "$lookup": {
            "from": "kbo_establishment",
            "let": {"enterpriseNum": "$EnterpriseNumber"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$EnterpriseNumber", "$$enterpriseNum"]}}},
                *_detail_lookups("EstablishmentNumber"),
            ],
            "as": "establishments",
        }
    }


def _branches_lookup() -> dict:
    return {
        "$lookup": {
            "from": "kbo_branch",
            "let": {"enterpriseNum": "$EnterpriseNumber"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$EnterpriseNumber", "$$enterpriseNum"]}}},
                *_detail_lookups("Id"),
            ],
            "as": "branches",
        }
    }


def build_entreprise_pipeline() -> list:
    return [
        *_detail_lookups("EnterpriseNumber"),
        _establishments_lookup(),
        _branches_lookup(),
        {"$addFields": {"_id": "$EnterpriseNumber"}},
        {"$merge": {"into": "entreprise", "whenMatched": "replace", "whenNotMatched": "insert"}},
    ]


def run_join(db):
    pipeline = build_entreprise_pipeline()
    db.kbo_enterprise.aggregate(pipeline, allowDiskUse=True)
    print("jointure terminee -- collection `entreprise` a jour")

def verify(db):
    with_establishment = db.entreprise.find_one({"establishments.0": {"$exists": True}})
    with_branch = db.entreprise.find_one({"branches.0": {"$exists": True}})
    print("\n--- exemple avec etablissement(s) ---")
    print(with_establishment)
    print("\n--- exemple avec succursale(s) ---")
    print(with_branch)


def main():
    db = get_db()
    load_all(db)
    create_indexes(db)
    run_join(db)
    verify(db)


if __name__ == "__main__":
    main()