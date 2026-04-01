import json

from langfuse import get_client, observe
from openai import OpenAI

from src.models import AlertTriage

openai_client = OpenAI()
langfuse_client = get_client()

SYSTEM_PROMPT = """
You are an infrastructure reliability assistant.
Extract information from the raw server log and output ONLY valid JSON.
The JSON must match this exact schema:
{
  "service_name": "<string - the exact microservice name>",
  "severity_level": "<LOW | MEDIUM | CRITICAL>",
  "is_database_issue": <true | false>
}
Do not include any explanation. Output raw JSON only.
"""


@observe(name="llm_extraction", as_type="generation")
def extract_triage_from_log(raw_log: str, model: str = "gpt-4o-mini") -> AlertTriage | None:
    """Call OpenAI and map JSON output to the AlertTriage schema."""
    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Log: {raw_log}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    if hasattr(langfuse_client, "update_current_generation"):
        langfuse_client.update_current_generation(
            model=model,
            model_parameters={"temperature": 0},
            metadata={"requested_model": model},
        )

    raw_json = response.choices[0].message.content or "{}"

    try:
        data = json.loads(raw_json)
        return AlertTriage(**data)
    except Exception:
        return None
