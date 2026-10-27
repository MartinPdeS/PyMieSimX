PyMieSimX
=========

.. image:: _static/logo.svg
   :alt: PyMieSimX
   :align: center
   :width: 520px

PyMieSimX is a Dash interface for configuring and exploring
`PyMieSim <https://martinpdes.github.io/PyMieSim/>`_ scattering simulations.
Use the web interface for interactive work, or call the lightweight Python API
from scripts and notebooks.

.. grid:: 1 2 3 3
   :gutter: 2

   .. grid-item-card:: Getting started
      :link: getting_started
      :link-type: doc

      Install PyMieSimX and start exploring simulations.

   .. grid-item-card:: How it works
      :link: how_it_works
      :link-type: doc

      Learn how the interface and calculations fit together.

   .. grid-item-card:: Sharing simulations
      :link: sharing
      :link-type: doc

      Share a simulation setup and export results.

   .. grid-item-card:: Reference
      :link: reference
      :link-type: doc

      Browse the Python API and graphical interface.

   .. grid-item-card:: Project
      :link: project
      :link-type: doc

      Find project and contribution information.

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: User guide

   getting_started
   how_it_works
   sharing
   Reference <reference>
   Project <project>

Key features
------------

* Configure single scatterer, parameter-scan, and ensemble optics studies.
* Explore scattering, absorption, extinction, efficiencies, and angular plots.
* Share a complete simulation setup with a URL and export computed results as
  CSV files.
* Use the same calculations without starting Dash through the Python API.

The scientific solver and material catalogue are provided by PyMieSim and
PyOptik. PyMieSimX focuses on the user interface, validation, plotting, and
export workflows around them.
