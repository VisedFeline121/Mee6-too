"""Entry point: wires everything together"""

import asyncio
import os
from utils.config_loader import load_config
from state import store
from core import scheduler, pipeline
from discord_client import DiscordClient


# Global references
_config = None
_discord_client: DiscordClient = None


async def check_followups():
    """Periodic task to check for users needing follow-ups."""
    try:
        followups = await store.get_pending_followups(hours_since=2)
        
        for followup in followups:
            context = {
                'guild_id': followup['guild_id'],
                'channel_id': followup['channel_id'],
                'user_id': followup['user_id'],
                'recent_messages': [],
                'context_json': {
                    'interest_type': followup['event_type'],
                    'confidence': followup['confidence']
                }
            }
            
            await pipeline.initiate_interaction(
                followup['channel_id'],
                followup['user_id'],
                context,
                _config,
                store,
                _discord_client
            )
    except Exception as e:
        print(f"Followup check error: {e}")


async def handle_message(event: dict):
    """Handle incoming Discord message event."""
    # Build context from event
    context = {
        'guild_id': event.get('guild_id', ''),
        'channel_id': event.get('channel_id', ''),
        'user_id': event.get('user_id', ''),
        'recent_messages': [
            {
                'user': event.get('author', 'Unknown'),
                'content': event.get('content', '')
            }
        ],
        'context_json': {}
    }
    
    await pipeline.process_event(
        event,
        context,
        _config,
        store,
        _discord_client
    )


async def main():
    """Initialize and run the bot."""
    global _config, _discord_client
    
    # Load config
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')
    _config = load_config(config_path)
    
    # Initialize database
    db_path = _config.get('database', {}).get('path', 'data/bot.db')
    await store.init_db(db_path)
    print(f"Database initialized at {db_path}")
    
    # Initialize scheduler
    sched = scheduler.init_scheduler()
    print("Scheduler initialized")
    
    # Initialize Discord client (teammate provides implementation)
    # For now, this is a placeholder - teammate will implement DiscordClient
    # _discord_client = YourDiscordClientImplementation()
    # _discord_client.on_message(handle_message)
    
    # Schedule periodic followup check (every hour with jitter)
    scheduler.schedule_periodic_task(check_followups, interval_seconds=3600, jitter=True)
    print("Periodic followup task scheduled")
    
    # Keep running
    print("Backend ready. Waiting for Discord client connection...")
    try:
        # Wait indefinitely (Discord client will handle event loop)
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        await store.close_db()
        sched.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
