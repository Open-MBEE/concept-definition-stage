"""cds.oracle — the model-conformance oracle service (spec §6.0 C2).

Stateless verification: a model *instance* (Turtle) in, a conformance verdict + granular
tri-severity findings out. "Build it right" is this service's whole job; "build the right
thing" (validation) belongs to the human commit gate. Surface: exactly ``POST /verify``,
``GET /rules``, ``GET /healthz``.
"""
