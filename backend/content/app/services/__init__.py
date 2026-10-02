"""Business logic.

Services know nothing about HTTP. They take plain Python values and a database
session, apply the rules of the product, and return models or raise AppError.
This keeps the rules testable without a web server and reusable from scripts.
"""
