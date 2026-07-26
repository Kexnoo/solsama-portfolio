import os
import openai

from core.memory import load_sister_memory, conversation_history, log_sister_message
from utils.text_utils import sanitize_reply, strip_speaker_prefixes


openai.api_key = os.environ.get("OPENAI_API_KEY")


async def get_gpt_reply(prompt: str, speaker: str = "Sol") -> str:
    # Load recent shared memory (last 20 lines)
    memory_lines = load_sister_memory()
    memory_text = "\n".join(memory_lines)

    # Inject memory into system prompt
    conversation_with_memory = conversation_history + [
        {"role": "system", "content": f"Shared memory so far:\n{memory_text}"}
    ]

    # Add user prompt
    conversation_with_memory.append({"role": "user", "content": prompt})

    # Ask GPT (non-streaming call)
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation_with_memory,
        temperature=1.2,
        top_p=0.9,
    )

    reply = response.choices[0].message.content
    reply = strip_speaker_prefixes(reply)
    reply = sanitize_reply(reply)

    # Update local conversation memory and log
    conversation_history.append({"role": "user", "content": prompt})
    conversation_history.append({"role": "assistant", "content": reply})
    log_sister_message(speaker, reply)

    return reply
