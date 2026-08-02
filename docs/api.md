# API reference

Auto-generated from docstrings (Sphinx autodoc + napoleon). The public surface is the `cds` CLI; these
modules are the library underneath it.

## Workspace & authoring

```{eval-rst}
.. automodule:: cds.core.workspace
   :members:
   :undoc-members:

.. automodule:: cds.core.authoring
   :members:
   :undoc-members:
```

## Models

```{eval-rst}
.. automodule:: cds.core.model.instances
   :members:
   :undoc-members:

.. automodule:: cds.core.model.notes
   :members:
   :undoc-members:
```

## Verification & views

```{eval-rst}
.. automodule:: cds.core.verify
   :members:
   :undoc-members:

.. automodule:: cds.core.compile
   :members:
   :undoc-members:
```

## Contracts, tool boundary & services

The cross-component seams and the service surfaces built on them (see the
[factoring contract](architecture/factoring.md) and the per-service pages under
`docs/services/`). Transport SDKs are imported lazily, so these modules document on a lean
install.

```{eval-rst}
.. automodule:: cds.contracts
   :members:
   :undoc-members:

.. automodule:: cds.mcp.tools
   :members:
   :undoc-members:

.. automodule:: cds.mcp.server
   :members:
   :undoc-members:

.. automodule:: cds.facilitator.server
   :members:
   :undoc-members:

.. automodule:: cds.oracle.app
   :members:
   :undoc-members:
```
