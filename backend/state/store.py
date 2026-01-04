"""SQLite state store"""

import aiosqlite
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import os


# Database connection pool (single connection for SQLite)
_db_connection: Optional[aiosqlite.Connection] = None


async def init_db(db_path: str) -> None:
    """Initialize database and create tables if they don't exist."""
    global _db_connection
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
    
    _db_connection = await aiosqlite.connect(db_path)
    _db_connection.row_factory = aiosqlite.Row
    
    # Create tables
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            guild_id TEXT,
            channel_id TEXT,
            user_id TEXT,
            last_interaction_at TIMESTAMP,
            context_json TEXT,
            PRIMARY KEY (guild_id, channel_id, user_id)
        )
    """)
    
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS cooldowns (
            entity_type TEXT,
            entity_id TEXT,
            expires_at TIMESTAMP,
            reason TEXT,
            PRIMARY KEY (entity_type, entity_id)
        )
    """)
    
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            event_type TEXT,
            guild_id TEXT,
            channel_id TEXT,
            user_id TEXT,
            timestamp TIMESTAMP,
            policy_outcome TEXT,
            reason_codes TEXT,
            selected_action TEXT,
            delivery_timing_ms INTEGER,
            response_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await _db_connection.execute("""
        CREATE TABLE IF NOT EXISTS interest_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            channel_id TEXT,
            user_id TEXT,
            event_type TEXT,
            confidence REAL,
            context_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    await _db_connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp 
        ON audit_log(timestamp)
    """)
    
    await _db_connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_log_guild_channel 
        ON audit_log(guild_id, channel_id)
    """)
    
    await _db_connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_cooldowns_expires 
        ON cooldowns(expires_at)
    """)
    
    await _db_connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_interest_log_user 
        ON interest_log(user_id, created_at)
    """)
    
    await _db_connection.commit()


async def get_conversation(guild_id: str, channel_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get conversation state."""
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    cursor = await _db_connection.execute("""
        SELECT guild_id, channel_id, user_id, last_interaction_at, context_json
        FROM conversations
        WHERE guild_id = ? AND channel_id = ? AND user_id = ?
    """, (guild_id, channel_id, user_id))
    
    row = await cursor.fetchone()
    if row is None:
        return None
    
    return {
        'guild_id': row['guild_id'],
        'channel_id': row['channel_id'],
        'user_id': row['user_id'],
        'last_interaction_at': row['last_interaction_at'],
        'context_json': json.loads(row['context_json']) if row['context_json'] else {}
    }


async def update_conversation(guild_id: str, channel_id: str, user_id: str, state: Dict[str, Any]) -> None:
    """Update conversation state."""
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    context_json = json.dumps(state.get('context_json', {}))
    last_interaction_at = state.get('last_interaction_at', datetime.utcnow().isoformat())
    
    await _db_connection.execute("""
        INSERT OR REPLACE INTO conversations 
        (guild_id, channel_id, user_id, last_interaction_at, context_json)
        VALUES (?, ?, ?, ?, ?)
    """, (guild_id, channel_id, user_id, last_interaction_at, context_json))
    
    await _db_connection.commit()


async def check_cooldown(entity_type: str, entity_id: str) -> Optional[datetime]:
    """Check if cooldown exists and return expires_at or None."""
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    cursor = await _db_connection.execute("""
        SELECT expires_at FROM cooldowns
        WHERE entity_type = ? AND entity_id = ?
    """, (entity_type, entity_id))
    
    row = await cursor.fetchone()
    if row is None:
        return None
    
    expires_at = datetime.fromisoformat(row['expires_at'])
    now = datetime.utcnow()
    
    # If expired, remove it and return None
    if expires_at < now:
        await _db_connection.execute("""
            DELETE FROM cooldowns
            WHERE entity_type = ? AND entity_id = ?
        """, (entity_type, entity_id))
        await _db_connection.commit()
        return None
    
    return expires_at


async def set_cooldown(entity_type: str, entity_id: str, seconds: int, reason: str) -> None:
    """Set cooldown."""
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    expires_at = (datetime.utcnow() + timedelta(seconds=seconds)).isoformat()
    
    await _db_connection.execute("""
        INSERT OR REPLACE INTO cooldowns 
        (entity_type, entity_id, expires_at, reason)
        VALUES (?, ?, ?, ?)
    """, (entity_type, entity_id, expires_at, reason))
    
    await _db_connection.commit()


async def log_decision(decision_trace: Dict[str, Any]) -> None:
    """Log policy decision."""
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    reason_codes_json = json.dumps(decision_trace.get('reason_codes', []))
    
    await _db_connection.execute("""
        INSERT INTO audit_log 
        (event_id, event_type, guild_id, channel_id, user_id, timestamp,
         policy_outcome, reason_codes, selected_action, delivery_timing_ms, response_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        decision_trace.get('event_id'),
        decision_trace.get('event_type'),
        decision_trace.get('guild_id'),
        decision_trace.get('channel_id'),
        decision_trace.get('user_id'),
        decision_trace.get('timestamp', datetime.utcnow().isoformat()),
        decision_trace.get('policy_outcome'),
        reason_codes_json,
        decision_trace.get('selected_action'),
        decision_trace.get('delivery_timing_ms'),
        decision_trace.get('response_text')
    ))
    
    await _db_connection.commit()


async def log_interest(interest_event: Dict[str, Any]) -> None:
    """Log interest detection."""
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    context_json = json.dumps(interest_event.get('context_json', {}))
    
    await _db_connection.execute("""
        INSERT INTO interest_log 
        (guild_id, channel_id, user_id, event_type, confidence, context_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        interest_event.get('guild_id'),
        interest_event.get('channel_id'),
        interest_event.get('user_id'),
        interest_event.get('event_type'),
        interest_event.get('confidence'),
        context_json
    ))
    
    await _db_connection.commit()


async def get_pending_followups(hours_since: int = 2) -> List[Dict[str, Any]]:
    """Query interest_log for users needing follow-ups."""
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    cutoff_time = (datetime.utcnow() - timedelta(hours=hours_since)).isoformat()
    
    cursor = await _db_connection.execute("""
        SELECT DISTINCT guild_id, channel_id, user_id, event_type, confidence, created_at
        FROM interest_log
        WHERE created_at >= ?
        ORDER BY created_at DESC
    """, (cutoff_time,))
    
    rows = await cursor.fetchall()
    return [
        {
            'guild_id': row['guild_id'],
            'channel_id': row['channel_id'],
            'user_id': row['user_id'],
            'event_type': row['event_type'],
            'confidence': row['confidence'],
            'created_at': row['created_at']
        }
        for row in rows
    ]


async def close_db() -> None:
    """Close database connection."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
