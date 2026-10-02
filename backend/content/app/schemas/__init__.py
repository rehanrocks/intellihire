"""Pydantic schemas.

Schemas are the *contract* between frontend and backend. A request body that
does not match its schema is rejected with HTTP 422 before our code runs;
a response is filtered to exactly the fields of its schema, so a password
hash can never leak by accident.
"""
