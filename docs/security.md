# Security and execution boundaries

Users belong to an organization. Projects require organization ownership and project
membership unless the user is an organization administrator. Editor/admin roles are required
for mutation. Cross-tenant resources return 404. Registration creates a separate organization;
it does not grant access to demo data. Administrative membership management is project-scoped.

Passwords use Argon2. JWTs validate issuer, audience, algorithm and expiry. Refresh tokens
are random, stored as hashes, rotated atomically and sent in HttpOnly SameSite=Strict cookies.
Replay revokes the token family. Logout revokes the refresh session; previously issued access
JWTs retain their short expiry. TLS deployments must enable secure cookies and a fixed CORS origin.
Redis rate limits authentication attempts. Request validation errors exclude raw input values.

Provider/database credentials live in ignored environment files or administrator environment
variables. Embedded credential fields in model/runtime configuration are rejected. Trace
keys/patterns are redacted. Sandbox subprocesses use an environment allowlist; HTTP MCP
containers receive only their synthetic token. Production credentials must not be used for attacks.

The platform never loads uploaded Python modules. Only administrator-installed adapters run.
Generic HTTP adapters require external mode, an exact administrator-origin allowlist and a
fixed administrator token environment. Redirects are disabled. Native adapters read inspected
snapshot endpoints with separate token variables. Do not allowlist production financial systems.

MCP fixtures are data only. No sandbox tool executes a shell, arbitrary URL, real payment,
or real correction. Permissions are independent of retrieved text. Approval resolution is
driver-only; simulated correction independently checks scope/status and idempotency.

Compose exposes loopback ports and runs application/frontend processes as non-root. The
local reference uses an internal trusted service network and generated development secrets.
It does not implement a compliance program, production secret manager, distributed side-effect
fencing, an OS-level untrusted-code sandbox, or a public multi-tenant deployment hardening guide.
The worker lease and known recovery delay are documented rather than claimed as exactly-once execution.
