"""Local text LLM through Ollama. The model is unloaded after each call so the GPU is free
for the image model (keep_alive=0)."""
import os


def ask(prompt, system="", json_mode=False, model=None):
    import ollama
    model = model or os.getenv("AGENT_MODEL", "agent-coder")
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    r = ollama.chat(model=model, messages=msgs, think=False, keep_alive=0,
                    format="json" if json_mode else None,
                    options={"temperature": 0.4, "num_ctx": 8192})
    return r["message"]["content"].strip()
