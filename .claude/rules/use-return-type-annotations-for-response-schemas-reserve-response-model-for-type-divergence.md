---
glob: "**/*.py"
---

<rule_activation adr-id="d94000db-4cff-424c-8892-60a030204674">
<!-- ADR: Use Return Type Annotations for Response Schemas; Reserve response_model= for Type Divergence -->
</rule_activation>

- Annotate route return types (-> UserOut) to let FastAPI infer the response model automatically
- Use response_model= only when the function return type and the desired output schema differ
