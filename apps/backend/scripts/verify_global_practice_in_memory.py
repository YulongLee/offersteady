"""Run candidate provider contracts in a separate process using a stdin bundle.

No deployment, database access or file writes. The parent supplies exact candidate
module/prompt text, not credentials. Existing Docker environment stays server-side.
"""
import importlib
import sys
import types


class Assets:
    def __init__(self, path=""):
        self.path = path

    def __truediv__(self, part):
        return Assets((self.path + "/" + part).lstrip("/"))

    def read_text(self, **kwargs):
        return BUNDLE["assets"][self.path]


for name, source in BUNDLE["modules"].items():
    parent, _, child = name.rpartition(".")
    importlib.import_module(parent)
    module = types.ModuleType(name)
    module.__package__ = parent
    module.__file__ = "/app/apps/backend/" + name.replace(".", "/") + ".py"
    sys.modules[name] = module
    setattr(sys.modules[parent], child, module)
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    if name.endswith(("mock_interview_generation", "mock_interview_tts")):
        module.REPO_ROOT = Assets()

from app.core.config import get_settings

assert get_settings().product_edition == "global", "Global settings required"
namespace = {"__name__": "provider_qa", "__file__": "synthetic-provider-qa.py"}
exec(compile(BUNDLE["runner"], "synthetic-provider-qa.py", "exec"), namespace)
namespace["REPO_ROOT"] = Assets()
sys.argv = ["synthetic-provider-qa", "--evals"] if "--evals-only" in sys.argv else ["synthetic-provider-qa", "--tts-asr", "--evals"]
import asyncio
asyncio.run(namespace["main"]())
