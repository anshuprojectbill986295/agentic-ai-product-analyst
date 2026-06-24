import os

try:
    import ollama
except ImportError:
    ollama = None

from groq import Groq

def call_llm(system_prompt, user_message, temperature=0.0, max_output_tokens= None):
    """Routes LLM requests to Groq (Production) or Ollama (Development)"""
    if "GROQ_API_KEY" in os.environ:
        kwargs={}
        if max_output_tokens is not None:
            kwargs["max_tokens"]= max_output_tokens
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=temperature,
            **kwargs
        )
        return response.choices[0].message.content.strip()
    else:
        
        options={"temperature":temperature}
        if max_output_tokens is not None:
            options["num_predict"]= max_output_tokens
        if ollama is None:
            raise Exception(
                "GROQ_API_KEY not configured and Ollama not available."
            )

        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            options=options
        )
        return response["message"]["content"].strip()
