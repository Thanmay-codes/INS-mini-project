"""Minimal health endpoint shared by the server starters."""

from flask import Flask, jsonify


def create_health_app(name: str, role: str) -> Flask:
    app = Flask(name)

    @app.get("/health")
    def health():
        return jsonify(status="ok", role=role, stage="scaffold")

    return app
