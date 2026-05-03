# file: handlers/__init__.py

import importlib.util
import os


current_dir = os.path.dirname(__file__)

root_handlers_path = os.path.join(
    current_dir,
    "..",
    "main_handler.py"
)

spec = importlib.util.spec_from_file_location(
    "root_handlers",
    root_handlers_path
)

root_handlers = importlib.util.module_from_spec(spec)

spec.loader.exec_module(root_handlers)

process_update = root_handlers.process_update