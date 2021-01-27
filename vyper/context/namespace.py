import re

from vyper.exceptions import (
    CompilerPanic,
    NamespaceCollision,
    StructureException,
    UndeclaredDefinition,
)
from vyper.opcodes import OPCODES


class Namespace(dict):
    """
    Dictionary subclass that represents the namespace of a contract.

    Attributes
    ----------
    _scopes : List[Set]
        List of sets containing the key names for each scope
    """

    def __init__(self):
        super().__init__()
        self._scopes = []
        from vyper.context import environment
        from vyper.context.types import get_types
        from vyper.functions.functions import get_builtin_functions

        self.update(get_types())
        self.update(environment.get_constant_vars())
        self.update(get_builtin_functions())

    def __eq__(self, other):
        return self is other

    def __setitem__(self, attr, obj):
        self.validate_assignment(attr)

        if self._scopes:
            self._scopes[-1].add(attr)
        super().__setitem__(attr, obj)

    def __getitem__(self, key):
        if key not in self:
            raise UndeclaredDefinition(f"'{key}' has not been declared")
        return super().__getitem__(key)

    def __enter__(self):
        if not self._scopes:
            raise CompilerPanic("Context manager must be invoked via namespace.enter_scope()")

    def __exit__(self, exc_type, exc_value, traceback):
        if not self._scopes:
            raise CompilerPanic("Bad use of namespace as a context manager")
        for key in self._scopes.pop():
            del self[key]

    def enter_scope(self):
        """
        Enter a new scope within the namespace.

        Called as a context manager, e.g. `with namespace.enter_scope():`
        All items that are added within the context are removed upon exit.
        """
        from vyper.context import environment

        self._scopes.append(set())

        if len(self._scopes) == 1:
            # add mutable vars (`self`) to the initial scope
            self.update(environment.get_mutable_vars())

        return self

    def update(self, other):
        for key, value in other.items():
            self.__setitem__(key, value)

    def clear(self):
        super().clear()
        self.__init__()

    def validate_assignment(self, attr):
        if not re.match("^[_a-zA-Z][a-zA-Z0-9_]*$", attr):
            return StructureException(f"'{attr}' contains invalid character(s)")
        if attr in self:
            if attr not in [x for i in self._scopes for x in i]:
                raise NamespaceCollision(f"Cannot assign to '{attr}', it is a builtin")
            obj = super().__getitem__(attr)
            raise NamespaceCollision(f"'{attr}' has already been declared as a {obj}")
        if not self._scopes:
            return
        if attr.lower() in RESERVED_KEYWORDS or attr.upper() in OPCODES:
            raise StructureException(f"'{attr}' is a reserved keyword")


def get_namespace():
    """
    Get the active namespace object.
    """
    global _namespace
    try:
        return _namespace
    except NameError:
        _namespace = Namespace()
        return _namespace


# Cannot be used for variable or member naming
RESERVED_KEYWORDS = {
    # decorators
    "public",
    "external",
    "nonpayable",
    "constant",
    "internal",
    "payable",
    "nonreentrant",
    # control flow
    "if",
    "for",
    "while",
    "until",
    "pass",
    "def",
    # EVM operations
    "send",
    "selfdestruct",
    "assert",
    "raise",
    "throw",
    # special functions (no name mangling)
    "init",
    "_init_",
    "___init___",
    "____init____",
    "default",
    "_default_",
    "___default___",
    "____default____",
    # environment variables
    "chainid",
    "blockhash",
    "timestamp",
    "timedelta",
    # boolean literals
    "true",
    "false",
    # more control flow and special operations
    "this",
    "continue",
    "range",
    # None sentinal value
    "none",
    # more special operations
    "indexed",
    # denominations
    "ether",
    "wei",
    "finney",
    "szabo",
    "shannon",
    "lovelace",
    "ada",
    "babbage",
    "gwei",
    "kwei",
    "mwei",
    "twei",
    "pwei",
    # `address` members
    "balance",
    "codesize",
    "is_contract",
    # units
    "units",
    # sentinal constant values
    "zero_address",
    "empty_bytes32",
    "max_int128",
    "min_int128",
    "max_decimal",
    "min_decimal",
    "max_uint256",
    "zero_wei",
}
