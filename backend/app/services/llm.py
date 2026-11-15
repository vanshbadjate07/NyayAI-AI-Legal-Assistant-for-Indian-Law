import ollama

from app.core.config import settings

_client = ollama.Client(host=settings.ollama_host)


def generate(prompt: str, system: str = "", temperature: float = None) -> str:
    """Calls the local Qwen2.5 model via Ollama. Raises a clear error if
    Ollama isn't running so the API layer can return a useful message."""
    if temperature is None:
        temperature = settings.llm_temperature
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = _client.chat(
            model=settings.llm_model,
            messages=messages,
            options={
                "temperature": temperature,
                # The retrieved context plus the prompt runs to a few
                # thousand tokens; the Ollama default of 2048 silently
                # truncates it, which drops the later passages.
                "num_ctx": settings.llm_num_ctx,
                # Bounds a runaway generation (observed: one unbounded
                # Marathi answer ran 24 minutes).
                "num_predict": settings.llm_num_predict,
            },
        )
    except Exception as e:
        raise RuntimeError(
            f"LLM call failed — is 'ollama serve' running and is "
            f"'{settings.llm_model}' pulled? Original error: {e}"
        )
    return response["message"]["content"].strip()
