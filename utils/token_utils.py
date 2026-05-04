def count_tokens(text: str, model: str | None = None) -> int:
    """Count tokens for a given text. Uses tiktoken if available, else a heuristic.

    Returns an integer token estimate.
    """
    try:
        import tiktoken

        # try to pick encoding for model if provided
        if model:
            try:
                enc = tiktoken.encoding_for_model(model)
            except Exception:
                enc = tiktoken.get_encoding("cl100k_base")
        else:
            enc = tiktoken.get_encoding("cl100k_base")

        return len(enc.encode(text))
    except Exception:
        # fallback heuristic: approximate tokens ~= characters / 4
        try:
            return max(1, int(len(text) / 4))
        except Exception:
            return len(text)


def count_messages_tokens(messages: list, model: str | None = None) -> int:
    """Count tokens for a list of chat messages (list of dicts with 'role' and 'content')."""
    total = 0
    for m in messages:
        content = m.get("content", "") if isinstance(m, dict) else str(m)
        total += count_tokens(content, model=model)
    return total
