"""LLM integration for response generation"""

import openai
from typing import Optional, Dict, Any


async def generate(context: Dict[str, Any], config: dict) -> Optional[str]:
    """Generate response using LLM."""
    try:
        llm_config = config.get('llm', {})
        api_key = llm_config.get('api_key')
        model = llm_config.get('model', 'gpt-4o-mini')
        temperature = llm_config.get('temperature', 0.7)
        
        if not api_key:
            return None
        
        client = openai.AsyncOpenAI(api_key=api_key)
        
        prompt = build_prompt(context)
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful Discord bot assistant. Keep responses concise and natural."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=200
        )
        
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content.strip()
        
        return None
        
    except Exception as e:
        # Log error but don't crash
        print(f"LLM generation error: {e}")
        return None


def build_prompt(context: Dict[str, Any]) -> str:
    """Format conversation history into prompt."""
    # Extract recent messages from context
    messages = context.get('recent_messages', [])
    
    if not messages:
        return "Generate a friendly greeting or acknowledgment."
    
    # Build prompt from recent messages
    prompt_parts = []
    for msg in messages[-5:]:  # Last 5 messages for context
        user = msg.get('user', 'User')
        content = msg.get('content', '')
        prompt_parts.append(f"{user}: {content}")
    
    prompt = "\n".join(prompt_parts)
    prompt += "\n\nGenerate an appropriate response:"
    
    return prompt
