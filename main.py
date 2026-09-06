"""Local development entry point.

Production deployments use Gunicorn (see Dockerfile).
"""
import os

from dashboard.app import app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8050"))
    app.run(host="0.0.0.0", port=port, debug=False)
