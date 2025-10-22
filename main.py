"""Entry point for the File Organizer AI desktop application."""
from __future__ import annotations

import logging

try:
    from .gui import FileOrganizerApp
except ImportError:  # pragma: no cover - fallback when run as script
    from gui import FileOrganizerApp


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def main() -> None:
    configure_logging()
    app = FileOrganizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
