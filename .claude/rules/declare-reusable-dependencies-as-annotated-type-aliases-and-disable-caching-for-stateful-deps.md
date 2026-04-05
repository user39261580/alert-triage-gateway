---
glob: "**/*.py"
---

<rule_activation adr-id="c02c4626-9c4e-47d1-ad72-6a5684e241f9">
<!-- ADR: Declare Reusable Dependencies as Annotated Type Aliases and Disable Caching for Stateful Deps -->
</rule_activation>

- Declare reusable dependencies as Annotated type aliases rather than inline Depends() default arguments
- Pass use_cache=False to Depends() for any dependency that must not be shared across call sites within a request
