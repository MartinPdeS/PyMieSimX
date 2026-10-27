How it works
============

PyMieSimX separates the interactive application from the optical calculations.
The Dash pages collect user input, validate it, and pass normalized values to
PyMieSim. Results are converted into tables and Plotly figures for the browser.

The main pieces are:

* **Setup and validation** normalize units, material choices, source settings,
  detector settings, and sweep bounds before a calculation starts.
* **PyMieSim** constructs the scatterer, source, and detector objects and
  computes the requested observables.
* **Background jobs** keep larger parameter scans away from the request thread
  and report queued, running, completed, and failed states to the UI.
* **Result guards** estimate dataframe and serialized payload sizes before a
  run, then check the actual result before it is sent to the browser.
* **Sharing** stores a validated configuration in a URL. Opening a shared URL
  restores the inputs and runs the setup again with the installed dependencies.

Material names are resolved by PyOptik and therefore follow the catalogue
available in the current environment. A direct ``n+ik`` value can be used when
an entry is not available.

Ensemble optics
---------------

The ensemble workflow evaluates a population of homogeneous spherical
particles at one wavelength. It supports monodisperse, truncated Gaussian,
lognormal, and uniform number-based diameter distributions. Cross sections are
averaged over the sampled population; effective anisotropy is weighted by
scattering cross section, and population albedo is the ratio of mean scattering
to mean extinction cross section.

Use dilute-population assumptions: particle interactions, multiple scattering,
and host-medium absorption are outside this model.
