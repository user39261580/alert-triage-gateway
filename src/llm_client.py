import json

from langfuse import get_client, observe
from opentelemetry import trace
from openai import OpenAI

from src.models import AlertTriage

openai_client = OpenAI()
langfuse_client = get_client()
tracer = trace.get_tracer("alert-triage-gateway")

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
    with tracer.start_as_current_span("llm_extraction") as span:
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.system", "openai")
        span.set_attribute("span.kind", "llm")

        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Log: {raw_log}"},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        usage = getattr(response, "usage", None)
        if usage is not None:
            if usage.prompt_tokens is not None:
                span.set_attribute("llm.usage.prompt_tokens", usage.prompt_tokens)
            if usage.completion_tokens is not None:
                span.set_attribute("llm.usage.completion_tokens", usage.completion_tokens)
            if usage.total_tokens is not None:
                span.set_attribute("llm.usage.total_tokens", usage.total_tokens)

        if hasattr(langfuse_client, "update_current_generation"):
            langfuse_client.update_current_generation(
                model=model,
                model_parameters={"temperature": 0},
                metadata={"requested_model": model},
            )

        raw_json = response.choices[0].message.content or "{}"

        try:
            data = json.loads(raw_json)
            span.set_attribute("llm.output.parse_success", True)
            return AlertTriage(**data)
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("llm.output.parse_success", False)
            return None
