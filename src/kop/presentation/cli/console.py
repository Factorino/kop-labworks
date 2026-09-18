from rich.console import Console


# Both streams are Consoles and dishka resolves by type, hence two empty
# subclasses to tell one from the other.


class OutConsole(Console): ...


class ErrConsole(Console): ...
