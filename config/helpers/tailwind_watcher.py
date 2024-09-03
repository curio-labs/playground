# tailwind_watcher.py
import logging
import subprocess

logger = logging.getLogger(__name__)


def run_tailwind_watch():
    """
    Runs TailwindCSS in watch mode for automatic recompilation.
    """
    command = [
        "./tailwindcss",  # Make sure that this points to your tailwindcss file in your project.
        "-i",
        "./app/static/css/input.css",  # input
        "-o",
        "./app/static/css/output.css",  # output
        "--watch",
    ]
    subprocess.run(command, check=False)
    logger.info("TailwindCSS watcher started.")


if __name__ == "__main__":
    run_tailwind_watch()
