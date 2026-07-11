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


def ask_ai(message: str, history: list[dict] | None = None, files_context: str | None = None, model_name: str | None = None) -> str:
    """
    Send a message (plus any prior turns for context) to the model and
    return the reply text. Raises ValueError on an empty/invalid response.

    history: list of {"sender": "user"|"bot", "content": str}, oldest first.
    files_context: optional text context extracted from uploaded files.
    model_name: custom model string to route the request to OpenRouter.
    """
    system_prompt = SYSTEM_PROMPT
    if files_context:
        system_prompt += f"\n\n--- UPLOADED FILES CONTEXT ---\nYou have access to the following files uploaded by the user. Use this information to answer their questions if relevant:\n{files_context}\n-----------------------------"

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        for turn in history:
            role = "assistant" if turn.get("sender") == "bot" else "user"
            messages.append({"role": role, "content": turn.get("content", "")})

    messages.append({"role": "user", "content": message})

    chosen_model = model_name or settings.MODEL_NAME

    completion = client.chat.completions.create(
        model=chosen_model,
        messages=messages,
        max_tokens=settings.MAX_TOKENS,
        temperature=0.7,
    )

    if not completion.choices:
        raise ValueError("No response from AI.")

    choice_message = completion.choices[0].message
    if choice_message is None or choice_message.content is None:
        raise ValueError("AI returned an empty message.")

    return choice_message.content
