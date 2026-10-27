Graphical interface
===================

The optional Dash interface is exposed through two helpers:

``create_dash_app``
   Create the configured Dash application for embedding in another service.

``OpticalSetupGUI``
   Construct the application wrapper used by the ``pymiesimx`` command.

These objects are imported lazily, so importing :mod:`PyMieSimX` for its
calculation API does not start a web server. The command-line entry point is
the recommended way to launch the complete interface.

.. automodule:: PyMieSimX.gui.interface
   :members: create_dash_app, OpticalSetupGUI
   :show-inheritance:
