"""Personal blog aggregator.

The package is organised into layers; the dependency rule between them is
enforced by import-linter (see ``.importlinter``):

    main -> presentation | infrastructure -> application -> domain

Nothing should live directly in this module: code belongs to one of the layers
below it.
"""
