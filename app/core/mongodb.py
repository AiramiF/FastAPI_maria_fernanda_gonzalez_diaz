import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import mongomock
from pymongo import MongoClient, ReturnDocument
from pymongo.database import Database
from pymongo.errors import PyMongoError

from .config import Settings

logger = logging.getLogger("biblioteca.database")


class Repository:
    def __init__(
        self,
        client: Any,
        database: Database[dict[str, Any]],
        mode: str,
    ) -> None:
        self.client = client
        self.database = database
        self.mode = mode
        self._create_indexes()

    def collection(self, name: str):
        return self.database[name]

    def get(self, collection: str, document_id: int) -> dict[str, Any] | None:
        return self.collection(collection).find_one({"id": document_id}, {"_id": 0})

    def insert(self, collection: str, document: dict[str, Any]) -> dict[str, Any]:
        data = _bson_values(document)
        if "id" not in data:
            counter = self.database["_counters"].find_one_and_update(
                {"_id": collection},
                {"$inc": {"value": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            data["id"] = counter["value"]
        data["_id"] = data["id"]
        self.collection(collection).insert_one(data)
        return {key: value for key, value in data.items() if key != "_id"}

    def update(
        self, collection: str, document_id: int, changes: dict[str, Any]
    ) -> dict[str, Any] | None:
        self.collection(collection).update_one(
            {"id": document_id}, {"$set": _bson_values(changes)}
        )
        return self.get(collection, document_id)

    def delete(self, collection: str, document_id: int) -> bool:
        return self.collection(collection).delete_one({"id": document_id}).deleted_count > 0

    def reset(self) -> None:
        for name in self.database.list_collection_names():
            if name != "_counters":
                self.database[name].delete_many({})
        self.database["_counters"].delete_many({})
        self._create_indexes()

    def close(self) -> None:
        self.client.close()

    def _create_indexes(self) -> None:
        for collection, field in (
            ("usuarios", "email"),
            ("socios", "email"),
            ("autores", "nombre"),
            ("categorias", "nombre"),
            ("libros", "isbn"),
            ("refresh_tokens", "jti"),
            ("multas", "prestamo_id"),
        ):
            self.collection(collection).create_index(field, unique=True)


def _bson_values(value: Any) -> Any:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _bson_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_bson_values(item) for item in value]
    return value


def connect_repository(settings: Settings) -> Repository:
    if settings.ENVIRONMENT == "test" or not settings.MONGODB_URI.strip():
        logger.warning("Biblioteca usando la base simulada en memoria")
        client = mongomock.MongoClient()
        return Repository(client, client[settings.MONGODB_DATABASE], "simulada")

    client: MongoClient[dict[str, Any]] | None = None
    try:
        client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=3000,
        )
        client.admin.command("ping")
    except PyMongoError as exc:
        if client is not None:
            client.close()
        logger.warning(
            "MongoDB Atlas no disponible (%s); se usará la base simulada en memoria",
            type(exc).__name__,
        )
        memory_client = mongomock.MongoClient()
        return Repository(
            memory_client,
            memory_client[settings.MONGODB_DATABASE],
            "simulada",
        )
    logger.info("Biblioteca conectada a MongoDB Atlas")
    assert client is not None
    return Repository(client, client[settings.MONGODB_DATABASE], "mongodb")
