from datetime import datetime, timedelta, timezone
from bson import ObjectId
from db import get_db


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

async def get_summary() -> dict:
    db = get_db()
    user_count = await db.users.count_documents({})
    convo_count = await db.conversations.count_documents({})
    msg_count = await db.messages.count_documents({})
    transaction_count = await db.transactions.count_documents({})

    # Total token consumption from transactions
    # tokenType: prompt = 输入, completion = 输出
    # tokenValue: 负数，取绝对值
    pipeline = [
        {"$group": {
            "_id": None,
            "totalPrompt": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "totalCompletion": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
        }}
    ]
    agg = await db.transactions.aggregate(pipeline).to_list(1)
    token_stats = agg[0] if agg else {}

    return {
        "user_count": user_count,
        "convo_count": convo_count,
        "msg_count": msg_count,
        "transaction_count": transaction_count,
        "total_input_tokens": int(token_stats.get("totalPrompt", 0)),
        "total_output_tokens": int(token_stats.get("totalCompletion", 0)),
    }


# ---------------------------------------------------------------------------
# Token consumption trend (daily, last N days)
# ---------------------------------------------------------------------------

async def get_token_trend(days: int = 30) -> list[dict]:
    db = get_db()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"createdAt": {"$gte": since}}},
        {"$group": {
            "_id": {
                "$dateToString": {"format": "%Y-%m-%d", "date": "$createdAt", "timezone": "Asia/Shanghai"}
            },
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "messageIds": {"$addToSet": {"$ifNull": ["$messageId", "$_id"]}},
        }},
        {"$addFields": {"count": {"$size": "$messageIds"}}},
        {"$project": {"messageIds": 0}},
        {"$sort": {"_id": 1}},
    ]
    result = await db.transactions.aggregate(pipeline).to_list(days)
    for r in result:
        r["promptTokens"] = int(r.get("promptTokens", 0))
        r["completionTokens"] = int(r.get("completionTokens", 0))
    return result


# ---------------------------------------------------------------------------
# Token by model
# ---------------------------------------------------------------------------

async def get_token_by_model() -> list[dict]:
    db = get_db()
    pipeline = [
        {"$group": {
            "_id": "$model",
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "messageIds": {"$addToSet": {"$ifNull": ["$messageId", "$_id"]}},
        }},
        {"$addFields": {"count": {"$size": "$messageIds"}}},
        # Only include models with actual token consumption (non-zero)
        {"$match": {
            "$or": [
                {"promptTokens": {"$ne": 0}},
                {"completionTokens": {"$ne": 0}},
            ]
        }},
        {"$project": {"messageIds": 0}},
        {"$sort": {"promptTokens": -1, "completionTokens": -1}},
    ]
    result = await db.transactions.aggregate(pipeline).to_list(50)
    for r in result:
        r["promptTokens"] = int(r.get("promptTokens", 0))
        r["completionTokens"] = int(r.get("completionTokens", 0))
    return result


# ---------------------------------------------------------------------------
# Top active users
# ---------------------------------------------------------------------------

async def get_top_users(limit: int = 10) -> list[dict]:
    db = get_db()
    pipeline = [
        {"$group": {
            "_id": "$user",
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "messageIds": {"$addToSet": {"$ifNull": ["$messageId", "$_id"]}},
        }},
        {"$addFields": {"msgCount": {"$size": "$messageIds"}}},
        {"$sort": {"msgCount": -1}},
        {"$limit": limit},
        {"$project": {"messageIds": 0}},
        {"$lookup": {
            "from": "users",
            "let": {"uid": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$_id", "$$uid"]}}},
                {"$project": {"name": 1, "email": 1, "username": 1}},
            ],
            "as": "userInfo",
        }},
        {"$unwind": {"path": "$userInfo", "preserveNullAndEmptyArrays": True}},
    ]
    result = await db.transactions.aggregate(pipeline).to_list(limit)
    for r in result:
        r["promptTokens"] = int(r.get("promptTokens", 0))
        r["completionTokens"] = int(r.get("completionTokens", 0))
    return result


# ---------------------------------------------------------------------------
# Token reconciliation — per user
# ---------------------------------------------------------------------------

async def get_token_by_user(
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    db = get_db()
    match_stage: dict = {}
    if start_date:
        match_stage.setdefault("createdAt", {})["$gte"] = datetime.fromisoformat(start_date)
    if end_date:
        match_stage.setdefault("createdAt", {})["$lte"] = datetime.fromisoformat(end_date)

    pipeline: list[dict] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline += [
        {"$group": {
            "_id": {"user": "$user", "model": "$model"},
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "messageIds": {"$addToSet": {"$ifNull": ["$messageId", "$_id"]}},
        }},
        {"$addFields": {"count": {"$size": "$messageIds"}}},
        # Only include records with actual token consumption (non-zero)
        {"$match": {
            "$or": [
                {"promptTokens": {"$ne": 0}},
                {"completionTokens": {"$ne": 0}},
            ]
        }},
        {"$project": {"messageIds": 0}},
        {"$lookup": {
            "from": "users",
            "let": {"uid": "$_id.user"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$_id", "$$uid"]}}},
                {"$project": {"name": 1, "email": 1, "username": 1}},
            ],
            "as": "userInfo",
        }},
        {"$unwind": {"path": "$userInfo", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"count": -1}},
    ]

    # Count total for pagination
    count_pipeline = pipeline + [{"$count": "total"}]
    count_result = await db.transactions.aggregate(count_pipeline).to_list(1)
    total = count_result[0]["total"] if count_result else 0

    # Paginate
    skip = (page - 1) * page_size
    data_pipeline = pipeline + [{"$skip": skip}, {"$limit": page_size}]
    items = await db.transactions.aggregate(data_pipeline).to_list(page_size)

    # Convert floats to ints
    for item in items:
        item["promptTokens"] = int(item.get("promptTokens", 0))
        item["completionTokens"] = int(item.get("completionTokens", 0))

    return {
        "records": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------------------------
# Token reconciliation — per model
# ---------------------------------------------------------------------------

async def get_token_by_model_detail(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    db = get_db()
    match_stage: dict = {}
    if start_date:
        match_stage.setdefault("createdAt", {})["$gte"] = datetime.fromisoformat(start_date)
    if end_date:
        match_stage.setdefault("createdAt", {})["$lte"] = datetime.fromisoformat(end_date)

    pipeline: list[dict] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline += [
        {"$group": {
            "_id": {"model": "$model", "tokenType": "$tokenType"},
            "tokenTotal": {"$sum": {"$abs": {"$ifNull": ["$tokenValue", 0]}}},
            "messageIds": {"$addToSet": {"$ifNull": ["$messageId", "$_id"]}},
        }},
        {"$addFields": {"count": {"$size": "$messageIds"}}},
        # Only include models with actual token consumption (non-zero)
        {"$match": {"tokenTotal": {"$ne": 0}}},
        {"$project": {"messageIds": 0}},
        {"$sort": {"_id.model": 1, "_id.tokenType": 1}},
    ]
    result = await db.transactions.aggregate(pipeline).to_list(100)
    for r in result:
        r["tokenTotal"] = int(r.get("tokenTotal", 0))
    return result


# ---------------------------------------------------------------------------
# User list for session browsing
# ---------------------------------------------------------------------------

async def get_user_list(
    search: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    db = get_db()
    match_stage: dict = {}
    if search:
        match_stage["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"username": {"$regex": search, "$options": "i"}},
        ]

    # Use aggregation to get users with conversation counts and sort
    pipeline = [
        {"$match": match_stage},
        {"$project": {"password": 0, "totpSecret": 0, "backupCodes": 0}},
        {"$lookup": {
            "from": "conversations",
            "let": {"uid": {"$toString": "$_id"}},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$user", "$$uid"]}}},
                {"$count": "count"}
            ],
            "as": "convoData"
        }},
        {"$addFields": {
            "convo_count": {"$ifNull": [{"$arrayElemAt": ["$convoData.count", 0]}, 0]},
        }},
        {"$lookup": {
            "from": "messages",
            "let": {"uid": {"$toString": "$_id"}},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$user", "$$uid"]}}},
                {"$count": "count"}
            ],
            "as": "msgData"
        }},
        {"$addFields": {
            "msg_count": {"$ifNull": [{"$arrayElemAt": ["$msgData.count", 0]}, 0]},
        }},
        {"$sort": {"convo_count": -1, "createdAt": -1}},
        {"$skip": (page - 1) * page_size},
        {"$limit": page_size},
        {"$project": {"convoData": 0, "msgData": 0}},
    ]

    users = await db.users.aggregate(pipeline).to_list(page_size)

    # Get total count for pagination
    total = await db.users.count_documents(match_stage)

    if not users:
        return {
            "records": [],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    # Batch fetch token stats
    user_object_ids = [u["_id"] for u in users]
    token_stats = {}
    async for doc in db.transactions.aggregate([
        {"$match": {"user": {"$in": user_object_ids}}},
        {"$group": {
            "_id": "$user",
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
        }}
    ]):
        doc["promptTokens"] = int(doc.get("promptTokens", 0))
        doc["completionTokens"] = int(doc.get("completionTokens", 0))
        token_stats[str(doc["_id"])] = doc

    # Enrich users with token stats
    for user in users:
        uid_str = str(user["_id"])
        stats = token_stats.get(uid_str, {})
        user["prompt_tokens"] = stats.get("promptTokens", 0)
        user["completion_tokens"] = stats.get("completionTokens", 0)

    return {
        "records": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------------------------
# Conversations for a user
# ---------------------------------------------------------------------------

async def get_user_conversations(
    user_id: str,
    page: int = 1,
    page_size: int = 30,
) -> dict:
    db = get_db()

    # user field in conversations is stored as string of ObjectId
    match = {"user": user_id}
    total = await db.conversations.count_documents(match)

    convos = (
        await db.conversations.find(match)
        .sort("updatedAt", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list(page_size)
    )

    if not convos:
        return {
            "records": [],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    # Batch fetch message counts
    convo_ids = [c.get("conversationId") for c in convos if c.get("conversationId")]
    msg_counts = {}
    if convo_ids:
        async for doc in db.messages.aggregate([
            {"$match": {"conversationId": {"$in": convo_ids}, "user": user_id}},
            {"$group": {"_id": "$conversationId", "count": {"$sum": 1}}}
        ]):
            msg_counts[doc["_id"]] = doc["count"]

    # Batch fetch token stats
    token_stats = {}
    if convo_ids:
        async for doc in db.transactions.aggregate([
            {"$match": {"conversationId": {"$in": convo_ids}, "user": ObjectId(user_id)}},
            {"$group": {
                "_id": "$conversationId",
                "promptTokens": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$tokenType", "prompt"]},
                            {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                            0
                        ]
                    }
                },
                "completionTokens": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$tokenType", "completion"]},
                            {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                            0
                        ]
                    }
                },
            }}
        ]):
            doc["promptTokens"] = int(doc.get("promptTokens", 0))
            doc["completionTokens"] = int(doc.get("completionTokens", 0))
            token_stats[doc["_id"]] = doc

    # Enrich conversations with pre-fetched data
    for c in convos:
        cid = c.get("conversationId")
        c["msg_count"] = msg_counts.get(cid, 0)
        stats = token_stats.get(cid, {})
        c["prompt_tokens"] = stats.get("promptTokens", 0)
        c["completion_tokens"] = stats.get("completionTokens", 0)

    return {
        "records": convos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------------------------
# Messages for a conversation
# ---------------------------------------------------------------------------

async def get_conversation_messages(
    conversation_id: str,
    user_id: str,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    db = get_db()
    match = {"conversationId": conversation_id, "user": user_id}
    total = await db.messages.count_documents(match)

    messages = (
        await db.messages.find(match)
        .sort("createdAt", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list(page_size)
    )

    # Extract text from content array if text field is empty
    for msg in messages:
        if not msg.get("text") and msg.get("content"):
            content = msg["content"]
            if isinstance(content, list):
                texts = []
                for item in content:
                    if isinstance(item, dict) and item.get("text"):
                        texts.append(item["text"])
                    elif isinstance(item, str):
                        texts.append(item)
                msg["content_text"] = "\n".join(texts) if texts else ""

    return {
        "records": messages,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------------------------
# Transactions for export (flat list, no pagination)
# ---------------------------------------------------------------------------

async def get_transactions_for_export(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    db = get_db()
    match_stage: dict = {}
    if start_date:
        match_stage.setdefault("createdAt", {})["$gte"] = datetime.fromisoformat(start_date)
    if end_date:
        match_stage.setdefault("createdAt", {})["$lte"] = datetime.fromisoformat(end_date)

    pipeline: list[dict] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline += [
        {"$addFields": {
            "tokenValueAbs": {"$abs": {"$ifNull": ["$tokenValue", 0]}},
        }},
        {"$lookup": {
            "from": "users",
            "let": {"uid": "$user"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$_id", "$$uid"]}}},
                {"$project": {"name": 1, "email": 1}},
            ],
            "as": "userInfo",
        }},
        {"$unwind": {"path": "$userInfo", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"createdAt": -1}},
    ]
    records = await db.transactions.aggregate(pipeline).to_list(10000)

    # Convert tokenValueAbs to int
    for r in records:
        r["tokenValueAbs"] = int(r.get("tokenValueAbs", 0))

    return records


# ---------------------------------------------------------------------------
# Conversation messages for export
# ---------------------------------------------------------------------------

async def get_messages_for_export(conversation_id: str, user_id: str) -> list[dict]:
    db = get_db()
    return (
        await db.messages.find(
            {"conversationId": conversation_id, "user": user_id}
        )
        .sort("createdAt", 1)
        .to_list(10000)
    )


# ---------------------------------------------------------------------------
# Usage records — detailed transaction log (merged by messageId)
# ---------------------------------------------------------------------------

async def get_usage_records(
    start_date: str | None = None,
    end_date: str | None = None,
    user_id: str | None = None,
    model: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """
    Get usage records grouped by messageId (prompt + completion merged).
    Each record contains: time, user, model, inputTokens, outputTokens.
    """
    db = get_db()
    match_stage: dict = {}

    # Date range filter
    if start_date:
        match_stage.setdefault("createdAt", {})["$gte"] = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        match_stage.setdefault("createdAt", {})["$lte"] = end_dt

    # User filter
    if user_id:
        match_stage["user"] = ObjectId(user_id)

    # Model filter (exact match)
    if model:
        match_stage["model"] = model

    pipeline: list[dict] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    # Group by messageId to merge prompt + completion
    pipeline += [
        {"$group": {
            "_id": "$messageId",
            "user": {"$first": "$user"},
            "model": {"$first": "$model"},
            "createdAt": {"$first": "$createdAt"},
            "conversationId": {"$first": "$conversationId"},
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
        }},
    ]

    # Count total for pagination
    count_pipeline = pipeline + [{"$count": "total"}]
    count_result = await db.transactions.aggregate(count_pipeline).to_list(1)
    total = count_result[0]["total"] if count_result else 0

    # Continue with user lookup and pagination
    pipeline += [
        {"$lookup": {
            "from": "users",
            "let": {"uid": "$user"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$_id", "$$uid"]}}},
                {"$project": {"name": 1, "email": 1, "username": 1}},
            ],
            "as": "userInfo",
        }},
        {"$unwind": {"path": "$userInfo", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"createdAt": -1}},
        {"$skip": (page - 1) * page_size},
        {"$limit": page_size},
    ]

    records = await db.transactions.aggregate(pipeline).to_list(page_size)

    # Convert to int
    for r in records:
        r["promptTokens"] = int(r.get("promptTokens", 0))
        r["completionTokens"] = int(r.get("completionTokens", 0))

    return {
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


async def get_distinct_models() -> list[str]:
    """Get all distinct model names from transactions."""
    db = get_db()
    models = await db.transactions.distinct("model")
    return sorted([m for m in models if m])


async def get_distinct_users_with_transactions() -> list[dict]:
    """Get users who have transactions for the filter dropdown."""
    db = get_db()
    pipeline = [
        {"$group": {"_id": "$user"}},
        {"$lookup": {
            "from": "users",
            "let": {"uid": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$_id", "$$uid"]}}},
                {"$project": {"name": 1, "email": 1}},
            ],
            "as": "userInfo",
        }},
        {"$unwind": {"path": "$userInfo", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"userInfo.name": 1}},
    ]
    return await db.transactions.aggregate(pipeline).to_list(1000)


async def get_usage_records_for_export(
    start_date: str | None = None,
    end_date: str | None = None,
    user_id: str | None = None,
    model: str | None = None,
) -> list[dict]:
    """Get all usage records for export (merged by messageId, no pagination)."""
    db = get_db()
    match_stage: dict = {}

    if start_date:
        match_stage.setdefault("createdAt", {})["$gte"] = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        match_stage.setdefault("createdAt", {})["$lte"] = end_dt

    if user_id:
        match_stage["user"] = ObjectId(user_id)

    if model:
        match_stage["model"] = model

    pipeline: list[dict] = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline += [
        {"$group": {
            "_id": "$messageId",
            "user": {"$first": "$user"},
            "model": {"$first": "$model"},
            "createdAt": {"$first": "$createdAt"},
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$tokenValue", 0]}},
                        0
                    ]
                }
            },
        }},
        {"$lookup": {
            "from": "users",
            "let": {"uid": "$user"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$_id", "$$uid"]}}},
                {"$project": {"name": 1, "email": 1}},
            ],
            "as": "userInfo",
        }},
        {"$unwind": {"path": "$userInfo", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"createdAt": -1}},
    ]

    records = await db.transactions.aggregate(pipeline).to_list(50000)

    for r in records:
        r["promptTokens"] = int(r.get("promptTokens", 0))
        r["completionTokens"] = int(r.get("completionTokens", 0))

    return records
