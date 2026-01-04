"""Main response pipeline: Event → Decision → Response → Deliver"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from state import store
from core import policy, scheduler
from llm import generator
from interest import detector


async def process_event(
    event: Dict[str, Any],
    context: Dict[str, Any],
    config: dict,
    store,
    client
) -> None:
    """Process a Discord event through the pipeline (reactive)."""
    try:
        # Policy check
        should_respond_flag, reason_codes = await policy.should_respond(
            event, context, config, store
        )
        
        if not should_respond_flag:
            # Log decision to skip
            await store.log_decision({
                'event_id': event.get('id', ''),
                'event_type': event.get('type', 'message'),
                'guild_id': event.get('guild_id', ''),
                'channel_id': event.get('channel_id', ''),
                'user_id': event.get('user_id', ''),
                'timestamp': datetime.utcnow().isoformat(),
                'policy_outcome': 'skip',
                'reason_codes': reason_codes,
                'selected_action': 'ignore',
                'delivery_timing_ms': None,
                'response_text': None
            })
            return
        
        # Check active window
        if not scheduler.is_active_window(config):
            await store.log_decision({
                'event_id': event.get('id', ''),
                'event_type': event.get('type', 'message'),
                'guild_id': event.get('guild_id', ''),
                'channel_id': event.get('channel_id', ''),
                'user_id': event.get('user_id', ''),
                'timestamp': datetime.utcnow().isoformat(),
                'policy_outcome': 'skip',
                'reason_codes': ['outside_window'],
                'selected_action': 'queue_for_later',
                'delivery_timing_ms': None,
                'response_text': None
            })
            return
        
        # Generate response
        response_text = await generator.generate(context, config)
        
        if not response_text:
            # LLM failed, log and skip
            await store.log_decision({
                'event_id': event.get('id', ''),
                'event_type': event.get('type', 'message'),
                'guild_id': event.get('guild_id', ''),
                'channel_id': event.get('channel_id', ''),
                'user_id': event.get('user_id', ''),
                'timestamp': datetime.utcnow().isoformat(),
                'policy_outcome': 'skip',
                'reason_codes': ['llm_failed'],
                'selected_action': 'skip',
                'delivery_timing_ms': None,
                'response_text': None
            })
            return
        
        # Get organic delay
        delay = scheduler.get_organic_delay(config)
        
        # Show typing indicator and wait
        channel_id = event.get('channel_id', '')
        await client.typing_indicator(channel_id, delay)
        await asyncio.sleep(delay)
        
        # Send message
        start_time = datetime.utcnow()
        await client.send_message(channel_id, response_text)
        delivery_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Set cooldowns
        await policy.set_cooldowns_after_response(event, config, store)
        
        # Log decision
        await store.log_decision({
            'event_id': event.get('id', ''),
            'event_type': event.get('type', 'message'),
            'guild_id': event.get('guild_id', ''),
            'channel_id': event.get('channel_id', ''),
            'user_id': event.get('user_id', ''),
            'timestamp': datetime.utcnow().isoformat(),
            'policy_outcome': 'respond',
            'reason_codes': reason_codes,
            'selected_action': 'generate_response',
            'delivery_timing_ms': delivery_time_ms,
            'response_text': response_text
        })
        
        # Check for interest
        interest_event = await detector.check(event, context, store)
        if interest_event:
            await store.log_interest(interest_event)
        
        # Update conversation state
        await store.update_conversation(
            event.get('guild_id', ''),
            event.get('channel_id', ''),
            event.get('user_id', ''),
            {
                'last_interaction_at': datetime.utcnow().isoformat(),
                'context_json': {
                    'recent_messages': context.get('recent_messages', [])[-10:]
                }
            }
        )
        
    except Exception as e:
        # Log error but don't crash
        print(f"Pipeline error: {e}")


async def initiate_interaction(
    channel_id: str,
    user_id: str,
    context: Dict[str, Any],
    config: dict,
    store,
    client
) -> None:
    """Initiate a conversation (proactive, from scheduled task)."""
    try:
        # Create synthetic event for policy check
        event = {
            'id': f"proactive_{datetime.utcnow().timestamp()}",
            'type': 'proactive',
            'guild_id': context.get('guild_id', ''),
            'channel_id': channel_id,
            'user_id': user_id,
            'content': ''
        }
        
        # Policy check
        should_respond_flag, reason_codes = await policy.should_respond(
            event, context, config, store
        )
        
        if not should_respond_flag:
            return
        
        # Check active window
        if not scheduler.is_active_window(config):
            return
        
        # Generate response
        response_text = await generator.generate(context, config)
        
        if not response_text:
            return
        
        # Get organic delay
        delay = scheduler.get_organic_delay(config)
        
        # Show typing indicator and wait
        await client.typing_indicator(channel_id, delay)
        await asyncio.sleep(delay)
        
        # Send message
        await client.send_message(channel_id, response_text)
        
        # Set cooldowns
        await policy.set_cooldowns_after_response(event, config, store)
        
        # Update conversation state
        await store.update_conversation(
            context.get('guild_id', ''),
            channel_id,
            user_id,
            {
                'last_interaction_at': datetime.utcnow().isoformat(),
                'context_json': context.get('context_json', {})
            }
        )
        
    except Exception as e:
        print(f"Initiate interaction error: {e}")
