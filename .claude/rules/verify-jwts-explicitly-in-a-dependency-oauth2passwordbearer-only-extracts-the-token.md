---
glob: "**/*.py"
---

<rule_activation adr-id="f177ce41-577e-4fd6-b975-2de8df7998b3">
<!-- ADR: Verify JWTs Explicitly in a Dependency — OAuth2PasswordBearer Only Extracts the Token -->
</rule_activation>

- Always decode and verify the JWT in a get_current_user dependency using jwt.decode(), not OAuth2PasswordBearer alone
- Use PyJWT for JWT handling — avoid python-jose (unmaintained) and passlib (known security vulnerabilities)
- Return WWW-Authenticate: Bearer in the headers of every 401 Unauthorized response
