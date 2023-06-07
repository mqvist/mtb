import importlib.util
from inspect import isclass
import sys
from dataclasses import dataclass
from system import System


@dataclass
class Model:
    systems: list[System]

    def get_system(self, name: str) -> System | None:
        for system in self.systems:
            if system.name == name:
                return system
        return None


def load_model_from_py_file(path) -> Model:
    spec = importlib.util.spec_from_file_location("model", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["model"] = module
    spec.loader.exec_module(module)
    # Extract systems
    systems = []
    for key, value in vars(module).items():
        if isclass(value):
            base_names = [cls.__name__ for cls in value.__bases__]
            # print(key, base_names)
            if "System" in base_names:
                systems.append(value())
    assert systems
    return Model(systems)
