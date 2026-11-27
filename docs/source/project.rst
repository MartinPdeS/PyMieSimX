Project
=======

Find guidance for sharing simulations and contributing to PyMieSimX.

.. toctree::
   :maxdepth: 2

   contributing

Server-side usage metrics
-------------------------

The dashboard can share a PostgreSQL metrics database with RosettaX. Configure
the Render service with::

    PYMIESIMX_USAGE_METRICS_BACKEND=postgres
    DATABASE_URL=<the shared PostgreSQL URL>

PyMieSimX writes namespaced counters to the shared ``metrics_counters`` table:
``pymiesimx_home_page_visit_count``, ``pymiesimx_experiment_run_count``, and
``pymiesimx_single_run_count``. Metrics are collected only when the PostgreSQL
backend is explicitly configured and available. Local installations do not
persist usage counters.

To show a small **Webapp visits** box in the homepage's top card, set this
environment variable on the Render service and redeploy::

    SHOW_METRIC=true

The box is hidden by default and requires the PostgreSQL configuration above.
It shows the total home-page visit count, including repeat visits, rather than
unique visitors. If the database is unavailable, the box stays hidden.

Administration page
-------------------

Detailed usage counters are shown on the hidden, token-protected administration
page. Configure a server-side token with::

    PYMIESIMX_ADMIN_TOKEN=<a long random value>

Then open ``/admin`` and enter the token on the sign-in page. A successful
sign-in grants access for 30 minutes. The page is intentionally absent
from the public sidebar and refreshes its counters every 30 seconds.

Recent activity shows the visit time, page and approximate location.
PyMieSimX sends the visitor's public IP address to IPinfo and displays the
available city, region and country. It caches lookups in server memory.
The visit history stores the resulting location. Local visits and failed
lookups display as unavailable.

On Render, optionally set ``PYMIESIMX_IPINFO_TOKEN`` to use your IPinfo
account and redeploy. The lookup also runs without a token.

Behind a reverse proxy, set ``PYMIESIMX_TRUSTED_PROXY_COUNT`` to the number
of trusted proxies that append addresses to ``X-Forwarded-For``. The
default is one on Render and zero for direct connections.

Docker Compose
--------------

From the checkout, run ``docker compose up --build`` and open
``http://localhost:8050``. Set ``PYMIESIMX_PORT=8051`` to run alongside
RosettaX on port 8050. To enable the admin page, export
``PYMIESIMX_ADMIN_TOKEN`` before starting Compose.

Compose forwards ``PYMIESIMX_IPINFO_TOKEN`` when set.
