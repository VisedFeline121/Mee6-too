"""Detect user engagement signals"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta


async def check(event: Dict[str, Any], context: Dict[str, Any], store) -> Optional[Dict[str, Any]]:
    """Check for interest signals. Returns interest_event or None."""
    guild_id = event.get('guild_id', '')
    channel_id = event.get('channel_id', '')
    user_id = event.get('user_id', '')
    message_content = event.get('content', '').lower()
    
    interest_signals = []
    confidence = 0.0
    
    # Check if bot was mentioned
    if '@bot' in message_content or '<@' in message_content:
        interest_signals.append('mention')
        confidence += 0.5
    
    # Check if message contains question marks
    if '?' in message_content:
        interest_signals.append('question')
        confidence += 0.3
    
    # Check if user sent multiple messages recently
    conversation = await store.get_conversation(guild_id, channel_id, user_id)
    if conversation:
        last_interaction = conversation.get('last_interaction_at')
        if last_interaction:
            try:
                last_time = datetime.fromisoformat(last_interaction)
                time_diff = (datetime.utcnow() - last_time).total_seconds()
                # If user sent message within last 60 seconds, high engagement
                if time_diff < 60:
                    interest_signals.append('high_engagement')
                    confidence += 0.4
            except (ValueError, TypeError):
                pass
    
    # Check message length (longer messages might indicate interest)
    if len(message_content) > 50:
        confidence += 0.1
    
    # Only return interest event if confidence is above threshold
    if confidence >= 0.3 and interest_signals:
        event_type = interest_signals[0]  # Primary signal
        if 'high_engagement' in interest_signals:
            event_type = 'high_engagement'
        elif 'mention' in interest_signals:
            event_type = 'mention'
        elif 'question' in interest_signals:
            event_type = 'question'
        
        return {
            'guild_id': guild_id,
            'channel_id': channel_id,
            'user_id': user_id,
            'event_type': event_type,
            'confidence': min(confidence, 1.0),
            'context_json': {
                'signals': interest_signals,
                'message_preview': message_content[:100]
            }
        }
    
    return None
