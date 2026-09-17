"""Custom Import Linter contract: an allow-list of external imports.

The built-in `forbidden` contract takes a deny-list, which has to grow with
every dependency the project adds and silently lets through anything nobody
thought to list. This contract inverts it: a module may import the standard
library and the external packages named in the contract, and nothing else.

Imports of the project's own modules are not checked here; the `layers`
contract in .importlinter orders those.

Registered in .importlinter under `contract_types`. Import Linter puts the
working directory on sys.path, which is what makes `scripts.import_contracts`
importable when `lint-imports` runs from the repository root.
"""

import sys
from typing import TYPE_CHECKING, cast, override

import grimp
from importlinter import Contract, ContractCheck, fields, output


if TYPE_CHECKING:
    from importlinter.domain.imports import Module


class AllowedExternalImportsContract(Contract):
    """Source modules import only the standard library and the allowed packages.

    Configuration options:
        - source_modules:  packages whose modules are checked, with all their
                           descendants.
        - allowed_modules: top-level external packages allowed in addition to
                           the standard library, e.g. `pydantic`. (Optional.)
    """

    type_name = "allowed_external_imports"

    source_modules = fields.ListField(subfield=fields.ModuleField())
    allowed_modules = fields.ListField(subfield=fields.StringField(), required=False, default=[])

    @override
    def check(self, graph: grimp.ImportGraph, verbose: bool) -> ContractCheck:
        """Collect every import of an external package that is not allowed.

        With `include_external_packages`, grimp represents the standard library
        and third-party packages alike as squashed top-level modules, so
        "squashed" is what tells an external import from one of our own.
        """
        allowed = set(sys.stdlib_module_names) | set(cast("list[str]", self.allowed_modules))
        violations: list[grimp.DetailedImport] = []

        for source in cast("list[Module]", self.source_modules):
            importers = {source.name} | graph.find_descendants(source.name)
            for importer in sorted(importers):
                for imported in sorted(graph.find_modules_directly_imported_by(importer)):
                    if graph.is_module_squashed(imported) and imported not in allowed:
                        violations.extend(
                            graph.get_import_details(importer=importer, imported=imported)
                        )

        return ContractCheck(kept=not violations, metadata={"violations": violations})

    @override
    def render_broken_contract(self, check: ContractCheck) -> None:
        """Print each disallowed import with its location."""
        for violation in check.metadata["violations"]:
            importer, imported = violation["importer"], violation["imported"]
            output.print_error(f"{importer} is not allowed to import {imported}:")
            output.new_line()
            output.indent_cursor()
            output.print_error(
                f"{importer}:{violation['line_number']}: {violation['line_contents']}",
                bold=False,
            )
            output.new_line()
