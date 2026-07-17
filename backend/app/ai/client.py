import re
from openai import OpenAI

from ..config.settings import settings

client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
)

SYSTEM_PROMPT = """
You are AI Nexus, an intelligent AI assistant created by Rajveer Singh.

Be friendly, professional, and helpful.

Never say you are Gemini unless the user specifically asks.

Help with:
- Programming
- AI
- Web Development
- SQL
- Python
- Java
- College studies
- General knowledge

IMAGE GENERATION OPTION:
If the user asks you to draw, paint, generate, or create an image, picture, or artwork, you must output a markdown image block referencing Pollinations.ai.
Format: ![Description](https://image.pollinations.ai/prompt/URL_ENCODED_PROMPT?width=1024&height=1024&nologo=true&seed=RANDOM_SEED)
Substitute URL_ENCODED_PROMPT with a descriptive prompt suitable for image generation, where spaces and special characters are url-encoded (e.g., "a%20cute%20cat"). Substitute RANDOM_SEED with a random integer.
Explain what you have drawn, then display the image block.
"""


def ask_ai(
    message: str,
    history: list[dict] | None = None,
    files_context: str | None = None,
    model_name: str | None = None,
    attached_images: list[dict] | None = None
) -> str:
    """
    Send a message (plus any prior turns for context) to the model and
    return the reply text. Raises ValueError on an empty/invalid response.

    history: list of {"sender": "user"|"bot", "content": str}, oldest first.
    files_context: optional text context extracted from uploaded files.
    model_name: custom model string to route the request to OpenRouter.
    attached_images: optional list of {"content_type": str, "base64_data": str}
    """
    system_prompt = SYSTEM_PROMPT
    if files_context:
        system_prompt += f"\n\n--- UPLOADED FILES CONTEXT ---\nYou have access to the following files uploaded by the user. Use this information to answer their questions if relevant:\n{files_context}\n-----------------------------"
    if attached_images:
        system_prompt += (
            "\n\nIMAGE ANALYSIS:\n"
            "The user has attached one or more images to this message. You CAN see and analyze them. "
            "Describe what you see and answer questions about the image content accurately. "
            "Do not say you cannot view or analyze images."
        )

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        for turn in history:
            role = "assistant" if turn.get("sender") == "bot" else "user"
            messages.append({"role": role, "content": turn.get("content", "")})

    if attached_images:
        content_parts = [{"type": "text", "text": message}]
        for img in attached_images:
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{img['content_type']};base64,{img['base64_data']}"
                }
            })
        messages.append({"role": "user", "content": content_parts})
    else:
        messages.append({"role": "user", "content": message})

    chosen_model = model_name or settings.MODEL_NAME
    current_max_tokens = settings.MAX_TOKENS
    completion = None

    for attempt in range(3):
        try:
            completion = client.chat.completions.create(
                model=chosen_model,
                messages=messages,
                max_tokens=current_max_tokens,
                temperature=0.7,
            )
            break
        except Exception as e:
            err_msg = str(e)
            is_402 = False
            if hasattr(e, "status_code") and e.status_code == 402:
                is_402 = True
            elif "402" in err_msg or "fewer max_tokens" in err_msg or "can only afford" in err_msg:
                is_402 = True

            if is_402 and attempt < 2:
                match = re.search(r"can only afford (\d+)", err_msg)
                if match:
                    afforded = int(match.group(1))
                    # Request slightly less than afforded to be safe, but at least 1
                    new_max_tokens = max(1, afforded - 5)
                    if new_max_tokens < current_max_tokens:
                        print(f"OpenRouter 402 error: requested {current_max_tokens}, can only afford {afforded}. Retrying with max_tokens={new_max_tokens}")
                        current_max_tokens = new_max_tokens
                        continue
                else:
                    new_max_tokens = current_max_tokens // 2
                    if new_max_tokens >= 50:
                        print(f"OpenRouter 402 error: Retrying with halved max_tokens={new_max_tokens}")
                        current_max_tokens = new_max_tokens
                        continue
            raise e

    if not completion or not completion.choices:
        raise ValueError("No response from AI.")

    choice_message = completion.choices[0].message
    if choice_message is None or choice_message.content is None:
        raise ValueError("AI returned an empty message.")

    return choice_message.content


def generate_conversation_title(first_message: str, model_name: str | None = None) -> str:
    """
    Generate a 3-5 word title for a conversation based on the user's first message.
    """
    chosen_model = model_name or settings.MODEL_NAME
    prompt = (
        f"Create a short, descriptive title (maximum 5 words, no quotes, no conversational filler, no trailing punctuation) "
        f"summarizing this message:\n\n{first_message}"
    )
    messages = [
        {"role": "system", "content": "You are a title generator. Return only the raw title text without punctuation or quotes."},
        {"role": "user", "content": prompt}
    ]
    try:
        completion = client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            max_tokens=20,
            temperature=0.5,
        )
        if completion.choices and completion.choices[0].message.content:
            title = completion.choices[0].message.content.strip().strip('"').strip("'").strip(".")
            return title[:60]
    except Exception as e:
        print(f"Error generating chat title: {e}")
    
    # Fallback to truncation
    fallback = first_message.strip()[:40]
    if len(first_message.strip()) > 40:
        fallback += "..."
    return fallback or "New Chat"
