from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
from bson import ObjectId

from app.config import settings


class MongoDB:

    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    async def connect(cls):
        try:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.MONGODB_DB_NAME]

            await cls.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")

            await cls.db.users.create_index("email", unique=True)
            await cls.db.chat_sessions.create_index("user_id")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")

    @classmethod
    def get_collection(cls, name: str):
        if cls.db is None:
            raise Exception("Database not connected")
        return cls.db[name]


class UserDB:

    @staticmethod
    async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        collection = MongoDB.get_collection("users")

        user_doc = {
            **user_data,
            "created_at": datetime.utcnow(),
            "is_active": True
        }

        result = await collection.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)

        return user_doc

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        collection = MongoDB.get_collection("users")
        user = await collection.find_one({"email": email})

        if user:
            user["_id"] = str(user["_id"])

        return user

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        collection = MongoDB.get_collection("users")

        try:
            user = await collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception:
            return None

    @staticmethod
    async def update_password(user_id: str, hashed_password: str) -> bool:
        """Update user password."""
        collection = MongoDB.get_collection("users")

        try:
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"hashed_password": hashed_password}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update password: {e}")
            return False

    @staticmethod
    async def update_profile(user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user profile information."""
        collection = MongoDB.get_collection("users")

        try:
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update profile: {e}")
            return False


class ChatDB:

    @staticmethod
    async def create_session(user_id: str, title: str) -> Dict[str, Any]:
        collection = MongoDB.get_collection("chat_sessions")

        session_doc = {
            "user_id": user_id,
            "title": title,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await collection.insert_one(session_doc)
        session_doc["_id"] = str(result.inserted_id)

        return session_doc

    @staticmethod
    async def add_message(session_id: str, message: Dict[str, Any]) -> bool:
        collection = MongoDB.get_collection("chat_sessions")

        try:
            result = await collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            return False

    @staticmethod
    async def get_user_sessions(user_id: str) -> list:
        collection = MongoDB.get_collection("chat_sessions")

        cursor = collection.find({"user_id": user_id}).sort("updated_at", -1)
        sessions = await cursor.to_list(length=100)

        for session in sessions:
            session["_id"] = str(session["_id"])

        return sessions

    @staticmethod
    async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        collection = MongoDB.get_collection("chat_sessions")

        try:
            session = await collection.find_one({"_id": ObjectId(session_id)})
            if session:
                session["_id"] = str(session["_id"])
            return session
        except Exception:
            return None

    @staticmethod
    async def delete_session(session_id: str) -> bool:
        collection = MongoDB.get_collection("chat_sessions")

        try:
            result = await collection.delete_one({"_id": ObjectId(session_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
