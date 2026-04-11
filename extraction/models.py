class Function:
    def __init__(self, name: str, file: str, calls: list[str]):
        self.name = name
        self.file = file
        self.calls = calls


class FileModule:
    def __init__(self, name: str, functions: list[Function]):
        self.name = name
        self.functions = functions
