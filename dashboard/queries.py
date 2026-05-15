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

    # Total token consumption + AI request count from transactions
    # tokenType: prompt = 输入, completion = 输出
    # rawAmount: 实际 token 数量，负数，取绝对值
    # 每次 AI 请求产生两条记录（prompt + completion），共享同一 messageId
    pipeline = [
        {"$group": {
            "_id": None,
            "totalPrompt": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "totalCompletion": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "messageIds": {"$addToSet": {"$ifNull": ["$messageId", "$_id"]}},
        }},
        {"$addFields": {"aiRequestCount": {"$size": "$messageIds"}}},
        {"$project": {"messageIds": 0}},
    ]
    agg = await db.transactions.aggregate(pipeline).to_list(1)
    token_stats = agg[0] if agg else {}

    total_input = int(token_stats.get("totalPrompt", 0))
    total_output = int(token_stats.get("totalCompletion", 0))
    ai_requests = int(token_stats.get("aiRequestCount", 0))

    return {
        "user_count": user_count,
        "convo_count": convo_count,
        "msg_count": msg_count,
        "ai_request_count": ai_requests,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "avg_input_tokens": total_input // ai_requests if ai_requests else 0,
        "avg_output_tokens": total_output // ai_requests if ai_requests else 0,
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
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
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
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
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
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
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

    base_pipeline: list[dict] = []
    if match_stage:
        base_pipeline.append({"$match": match_stage})

    # Group by user+model first
    base_pipeline += [
        {"$group": {
            "_id": {"user": "$user", "model": "$model"},
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "messageIds": {"$addToSet": {"$ifNull": ["$messageId", "$_id"]}},
        }},
        {"$addFields": {"count": {"$size": "$messageIds"}}},
        {"$match": {
            "$or": [
                {"promptTokens": {"$ne": 0}},
                {"completionTokens": {"$ne": 0}},
            ]
        }},
        {"$project": {"messageIds": 0}},
        # Regroup by user, collecting models into array
        {"$group": {
            "_id": "$_id.user",
            "models": {"$push": {
                "model": "$_id.model",
                "promptTokens": "$promptTokens",
                "completionTokens": "$completionTokens",
                "count": "$count",
            }},
            "totalPrompt": {"$sum": "$promptTokens"},
            "totalCompletion": {"$sum": "$completionTokens"},
            "totalCount": {"$sum": "$count"},
        }},
        {"$sort": {"totalCount": -1}},
    ]

    # Count distinct users
    count_pipeline = base_pipeline + [{"$count": "total"}]
    count_result = await db.transactions.aggregate(count_pipeline).to_list(1)
    total = count_result[0]["total"] if count_result else 0

    # Paginate users
    skip = (page - 1) * page_size
    data_pipeline = base_pipeline + [{"$skip": skip}, {"$limit": page_size}]
    items = await db.transactions.aggregate(data_pipeline).to_list(page_size)

    # Lookup user info
    user_ids = [item["_id"] for item in items if item.get("_id")]
    users_cursor = db.users.find(
        {"_id": {"$in": user_ids}},
        {"name": 1, "email": 1, "username": 1},
    )
    users_map: dict = {}
    async for u in users_cursor:
        users_map[u["_id"]] = u

    for item in items:
        item["userInfo"] = users_map.get(item["_id"])
        item["totalPrompt"] = int(item.get("totalPrompt", 0))
        item["totalCompletion"] = int(item.get("totalCompletion", 0))
        item["totalCount"] = int(item.get("totalCount", 0))
        for m in item.get("models", []):
            m["promptTokens"] = int(m.get("promptTokens", 0))
            m["completionTokens"] = int(m.get("completionTokens", 0))
            m["count"] = int(m.get("count", 0))
        item["models"].sort(key=lambda m: m["promptTokens"] + m["completionTokens"], reverse=True)
    items.sort(key=lambda x: x["totalPrompt"] + x["totalCompletion"], reverse=True)

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
            "_id": "$model",
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "messageIds": {"$addToSet": {"$ifNull": ["$messageId", "$_id"]}},
        }},
        {"$addFields": {"count": {"$size": "$messageIds"}}},
        {"$match": {
            "$or": [
                {"promptTokens": {"$ne": 0}},
                {"completionTokens": {"$ne": 0}},
            ]
        }},
        {"$project": {"messageIds": 0}},
    ]
    result = await db.transactions.aggregate(pipeline).to_list(100)
    grand_prompt = 0
    grand_completion = 0
    grand_count = 0
    for r in result:
        r["promptTokens"] = int(r.get("promptTokens", 0))
        r["completionTokens"] = int(r.get("completionTokens", 0))
        r["count"] = int(r.get("count", 0))
        grand_prompt += r["promptTokens"]
        grand_completion += r["completionTokens"]
        grand_count += r["count"]
    result.sort(key=lambda x: x["promptTokens"] + x["completionTokens"], reverse=True)
    return {
        "records": result,
        "grand_prompt": grand_prompt,
        "grand_completion": grand_completion,
        "grand_count": grand_count,
    }


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
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
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
                            {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                            0
                        ]
                    }
                },
                "completionTokens": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$tokenType", "completion"]},
                            {"$abs": {"$ifNull": ["$rawAmount", 0]}},
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

    # Extract text from content array if text field is empty,
    # and collect file/image references for display.
    file_ids_to_lookup: set[str] = set()

    for msg in messages:
        file_items: list[dict] = []

        # Process content array for text + non-text blocks
        if not msg.get("text") and msg.get("content"):
            content = msg["content"]
            if isinstance(content, list):
                texts = []
                for item in content:
                    if not isinstance(item, dict):
                        if isinstance(item, str):
                            texts.append(item)
                        continue
                    item_type = item.get("type")
                    if item_type == "text":
                        texts.append(item.get("text", ""))
                    elif item_type == "image_url":
                        url = item.get("image_url", {}).get("url", "")
                        if url:
                            file_items.append({"type": "image", "url": url})
                    elif item_type == "image_file":
                        fid = item.get("image_file", {}).get("file_id", "")
                        if fid:
                            file_ids_to_lookup.add(fid)
                            file_items.append({"type": "file_ref", "file_id": fid})
                msg["content_text"] = "\n".join(texts) if texts else ""

        # Also extract non-text blocks even when text field exists
        elif msg.get("content") and isinstance(msg["content"], list):
            for item in msg["content"]:
                if not isinstance(item, dict):
                    continue
                item_type = item.get("type")
                if item_type == "image_url":
                    url = item.get("image_url", {}).get("url", "")
                    if url:
                        file_items.append({"type": "image", "url": url})
                elif item_type == "image_file":
                    fid = item.get("image_file", {}).get("file_id", "")
                    if fid:
                        file_ids_to_lookup.add(fid)
                        file_items.append({"type": "file_ref", "file_id": fid})

        # Process files array
        if msg.get("files") and isinstance(msg["files"], list):
            for f in msg["files"]:
                if isinstance(f, dict):
                    fid = f.get("file_id", "")
                    if fid:
                        file_ids_to_lookup.add(fid)
                        file_items.append({"type": "file_ref", "file_id": fid})

        # Process attachments array
        if msg.get("attachments") and isinstance(msg["attachments"], list):
            for a in msg["attachments"]:
                if isinstance(a, dict):
                    fid = a.get("file_id", "")
                    fname = a.get("filename", "")
                    ftype = a.get("type", "")
                    if fid:
                        file_ids_to_lookup.add(fid)
                        file_items.append({"type": "file_ref", "file_id": fid})
                    elif fname:
                        file_items.append({"type": "file_ref", "filename": fname, "file_type": ftype})

        msg["file_items"] = file_items

    # Batch lookup file metadata from files collection
    if file_ids_to_lookup:
        files_cursor = db.files.find(
            {"file_id": {"$in": list(file_ids_to_lookup)}},
            {"file_id": 1, "filename": 1, "type": 1, "width": 1, "height": 1, "bytes": 1},
        )
        file_meta: dict[str, dict] = {}
        async for f in files_cursor:
            file_meta[f["file_id"]] = f
        for msg in messages:
            for item in msg.get("file_items", []):
                fid = item.get("file_id")
                if fid and fid in file_meta:
                    item["meta"] = file_meta[fid]

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
            "tokenValueAbs": {"$abs": {"$ifNull": ["$rawAmount", 0]}},
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

    if start_date:
        match_stage.setdefault("createdAt", {})["$gte"] = datetime.fromisoformat(start_date)
    if end_date:
        match_stage.setdefault("createdAt", {})["$lte"] = datetime.fromisoformat(end_date)
    if user_id:
        match_stage["user"] = ObjectId(user_id)
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
            "context": {"$first": "$context"},
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "inputTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$inputTokens", 0]}},
                        0
                    ]
                }
            },
            "writeTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$writeTokens", 0]}},
                        0
                    ]
                }
            },
            "readTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$readTokens", 0]}},
                        0
                    ]
                }
            },
        }},
        # $facet: count + paginated data in a single pass
        {"$facet": {
            "metadata": [{"$count": "total"}],
            "records": [
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
            ],
        }},
        {"$project": {
            "total": {"$ifNull": [{"$arrayElemAt": ["$metadata.total", 0]}, 0]},
            "records": 1,
        }},
    ]

    facet_result = await db.transactions.aggregate(pipeline).to_list(1)
    if not facet_result:
        return {
            "records": [], "total": 0, "page": page,
            "page_size": page_size, "total_pages": 0,
        }

    total = int(facet_result[0].get("total", 0))
    records = facet_result[0].get("records", [])

    # Batch-fetch duration: preceding user message per (conversationId, user)
    await _enrich_duration(db, records)

    for r in records:
        r["promptTokens"] = int(r.get("promptTokens", 0))
        r["completionTokens"] = int(r.get("completionTokens", 0))
        r["inputTokens"] = int(r.get("inputTokens", 0))
        r["writeTokens"] = int(r.get("writeTokens", 0))
        r["readTokens"] = int(r.get("readTokens", 0))

    return {
        "records": records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


async def _enrich_duration(db, records: list[dict]) -> None:
    """Batch-compute API duration for a page of records.

    Instead of a per-record $lookup into messages, this does batch
    queries per unique (conversationId, user) pair, then matches
    in Python with binary search.
    """
    if not records:
        return

    from bisect import bisect_left

    # Collect unique (conversationId, user_str) pairs
    pairs: set[tuple[str, str]] = set()
    for r in records:
        cid = r.get("conversationId")
        uid = r.get("user")
        if cid and uid:
            pairs.add((cid, str(uid)))

    if not pairs:
        return

    # Chunk the $or query to avoid oversized BSON documents (16MB limit)
    CHUNK = 500
    pair_list = list(pairs)
    # timestamps sorted ascending per pair
    msg_map: dict[tuple[str, str], list[datetime]] = {}

    for i in range(0, len(pair_list), CHUNK):
        chunk = pair_list[i : i + CHUNK]
        or_conditions = [
            {"conversationId": cid, "user": uid, "isCreatedByUser": True}
            for cid, uid in chunk
        ]
        cursor = db.messages.find(
            {"$or": or_conditions},
            {"conversationId": 1, "user": 1, "createdAt": 1},
        ).sort("createdAt", 1)
        async for msg in cursor:
            key = (msg["conversationId"], msg["user"])
            msg_map.setdefault(key, []).append(msg["createdAt"])

    # For each record, binary-search for the preceding user message
    for r in records:
        cid = r.get("conversationId")
        uid = r.get("user")
        tx_time = r.get("createdAt")
        if not (cid and uid and tx_time):
            r["duration"] = None
            continue

        timestamps = msg_map.get((cid, str(uid)))
        if not timestamps:
            r["duration"] = None
            continue

        # timestamps ascending; find rightmost ts < tx_time
        idx = bisect_left(timestamps, tx_time)
        if idx > 0:
            delta = tx_time - timestamps[idx - 1]
            r["duration"] = round(delta.total_seconds(), 1)
        else:
            r["duration"] = None


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
        match_stage.setdefault("createdAt", {})["$lte"] = datetime.fromisoformat(end_date)
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
            "conversationId": {"$first": "$conversationId"},
            "context": {"$first": "$context"},
            "promptTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "completionTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "completion"]},
                        {"$abs": {"$ifNull": ["$rawAmount", 0]}},
                        0
                    ]
                }
            },
            "inputTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$inputTokens", 0]}},
                        0
                    ]
                }
            },
            "writeTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$writeTokens", 0]}},
                        0
                    ]
                }
            },
            "readTokens": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$tokenType", "prompt"]},
                        {"$abs": {"$ifNull": ["$readTokens", 0]}},
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

    # Batch-compute duration instead of per-record $lookup to messages
    await _enrich_duration(db, records)

    for r in records:
        r["promptTokens"] = int(r.get("promptTokens", 0))
        r["completionTokens"] = int(r.get("completionTokens", 0))
        r["inputTokens"] = int(r.get("inputTokens", 0))
        r["writeTokens"] = int(r.get("writeTokens", 0))
        r["readTokens"] = int(r.get("readTokens", 0))

    return records


# ---------------------------------------------------------------------------
# File list for file management page
# ---------------------------------------------------------------------------

async def get_file_list(
    search: str = "",
    file_type: str = "",
    user_id: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    db = get_db()
    match_stage: dict = {}

    if search:
        match_stage["filename"] = {"$regex": search, "$options": "i"}

    if file_type == "image":
        match_stage["type"] = {"$regex": "^image/", "$options": "i"}
    elif file_type == "document":
        match_stage["type"] = {"$not": {"$regex": "^image/", "$options": "i"}}

    if user_id:
        match_stage["user"] = ObjectId(user_id)

    pipeline: list[dict] = [{"$match": match_stage}]

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
    ]

    count_pipeline = pipeline + [{"$count": "total"}]
    count_result = await db.files.aggregate(count_pipeline).to_list(1)
    total = count_result[0]["total"] if count_result else 0

    skip = (page - 1) * page_size
    data_pipeline = pipeline + [{"$skip": skip}, {"$limit": page_size}]
    items = await db.files.aggregate(data_pipeline).to_list(page_size)

    for item in items:
        item["bytes"] = int(item.get("bytes", 0))

    return {
        "records": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


async def get_file_stats() -> dict:
    db = get_db()
    pipeline = [
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "totalBytes": {"$sum": {"$ifNull": ["$bytes", 0]}},
            "imageCount": {
                "$sum": {"$cond": [{"$regexMatch": {"input": {"$ifNull": ["$type", ""]}, "regex": "^image/"}}, 1, 0]}
            },
        }}
    ]
    agg = await db.files.aggregate(pipeline).to_list(1)
    stats = agg[0] if agg else {}
    return {
        "total": int(stats.get("total", 0)),
        "totalBytes": int(stats.get("totalBytes", 0)),
        "imageCount": int(stats.get("imageCount", 0)),
        "docCount": int(stats.get("total", 0)) - int(stats.get("imageCount", 0)),
    }


async def get_file_users() -> list[dict]:
    """Get users who have uploaded files for the filter dropdown."""
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
    return await db.files.aggregate(pipeline).to_list(1000)


async def get_file_by_id(file_id: str) -> dict | None:
    """Retrieve a single file document by its file_id."""
    db = get_db()
    return await db.files.find_one({"file_id": file_id})
