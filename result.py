class Result:
    def __init__(self, module: int, description: int):
        self.module = module
        self.description = description

    def __str__(self) -> str:
        return f"Result(mod={self.module}, desc={self.description})"

    @property
    def failed(self) -> bool:
        return self.module != 0 or self.description != 0

    @property
    def succeeded(self) -> bool:
        return self.module == 0 and self.description == 0

    @classmethod
    def from_int(cls, value: int) -> "Result":
        return cls(value & 0x1FF, (value >> 9) & 0x1FFF)
