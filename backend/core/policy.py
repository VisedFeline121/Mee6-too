"""Policy engine: decides whether to respond to events"""

from datetime import datetime
from typing import Tuple, List, Dict, Any
from core import scheduler


async def should_respond(
    event: Dict[str, Any],
    context: Dict[str, Any],
    config: dict,
    store
) -> Tuple[bool, List[str]]:
    """
    Evaluate whether to respond to an event.
    Returns: (should_respond: bool, reason_codes: List[str])
    """
    reason_codes = []
    
    # Check global enabled flag
    if not config.get('policy', {}).get('enabled', True):
        return False, ['disabled']
    
    reason_codes.append('enabled')
    
    # Check active window
    if not scheduler.is_active_window(config):
        return False, ['outside_window']
    
    # Extract IDs from event
    guild_id = event.get('guild_id', '')
    channel_id = event.get('channel_id', '')
    user_id = event.get('user_id', '')
    
    # Check cooldowns
    cooldown_config = config.get('policy', {})
    
    # Check user cooldown
    user_cooldown = await store.check_cooldown('user', user_id)
    if user_cooldown:
        return False, ['cooldown_user']
    
    # Check channel cooldown
    channel_cooldown = await store.check_cooldown('channel', channel_id)
    if channel_cooldown:
        return False, ['cooldown_channel']
    
    # Check global cooldown
    global_cooldown = await store.check_cooldown('global', 'global')
    if global_cooldown:
        return False, ['cooldown_global']
    
    # All checks passed
    return True, reason_codes


async def set_cooldowns_after_response(
    event: Dict[str, Any],
    config: dict,
    store
) -> None:
    """Set cooldowns after responding."""
    guild_id = event.get('guild_id', '')
    channel_id = event.get('channel_id', '')
    user_id = event.get('user_id', '')
    
    cooldown_config = config.get('policy', {})
    
    # Set user cooldown
    user_cooldown_seconds = cooldown_config.get('cooldown_user_seconds', 60)
    await store.set_cooldown('user', user_id, user_cooldown_seconds, 'user_response')
    
    # Set channel cooldown
    channel_cooldown_seconds = cooldown_config.get('cooldown_channel_seconds', 30)
    await store.set_cooldown('channel', channel_id, channel_cooldown_seconds, 'channel_response')
    
    # Set global cooldown
    global_cooldown_seconds = cooldown_config.get('cooldown_global_seconds', 10)
    await store.set_cooldown('global', 'global', global_cooldown_seconds, 'global_response')
