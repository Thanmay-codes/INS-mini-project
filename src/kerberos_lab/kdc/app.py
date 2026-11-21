"""KDC server starter. Ticket endpoints belong to the next milestone."""

from flask import Flask

from kerberos_lab.common.web import create_health_app


def create_app() -> Flask:
    return create_health_app(__name__, "kdc")


def main() -> None:
    create_app().run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
