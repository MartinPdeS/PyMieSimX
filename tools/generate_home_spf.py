"""Generate the static high-resolution SPF preview used on the home page."""

from pathlib import Path

import numpy as np
from matplotlib import cm
from matplotlib.colors import Normalize
import matplotlib.pyplot as plt

from PyMieSimX.gui.computation import build_single_figure


OUTPUT_PATH = Path(__file__).parents[1] / "PyMieSimX" / "gui" / "assets" / "home-spf-radial.png"
CAMERA_ELEVATION = 18
CAMERA_AZIMUTH = 18


def main() -> None:
    figure, _summary = build_single_figure(
        source_type="Gaussian",
        source_values={},
        scatterer_type="Sphere",
        scatterer_values={"diameter": "100"},
        representation="spf",
        projection="3d_radial",
        sampling=300,
    )
    trace = figure.data[0]
    intensity = trace.surfacecolor

    # Keep the small-particle preview gentle and readable: a linear radial
    # scale preserves the dipole-like shape without exaggerating numerical
    # noise or collapsing the surface into a featureless sphere.
    values = np.asarray(intensity, dtype=float)
    azimuth = np.deg2rad(np.linspace(-180.0, 180.0, values.shape[1]))
    polar = np.deg2rad(np.linspace(-90.0, 90.0, values.shape[0]))
    azimuth_grid, polar_grid = np.meshgrid(azimuth, polar)
    sphere_x = np.cos(polar_grid) * np.cos(azimuth_grid)
    sphere_y = np.cos(polar_grid) * np.sin(azimuth_grid)
    sphere_z = np.sin(polar_grid)

    lower, upper = float(values.min()), float(values.max())
    normalized = (values - lower) / (upper - lower) if upper > lower else np.ones_like(values)
    radius = 0.24 + 0.76 * normalized

    x_values = sphere_x * radius
    y_values = sphere_y * radius
    z_values = sphere_z * radius
    colors = cm.viridis(Normalize(vmin=lower, vmax=upper)(values))

    output = plt.figure(figsize=(10, 8), dpi=320, facecolor="none")
    axes = output.add_subplot(111, projection="3d")
    axes.set_facecolor((0, 0, 0, 0))
    axes.plot_surface(
        x_values,
        y_values,
        z_values,
        facecolors=colors,
        rcount=x_values.shape[0],
        ccount=x_values.shape[1],
        linewidth=0,
        antialiased=True,
        shade=False,
    )
    axes.set_proj_type("ortho")
    axes.view_init(elev=CAMERA_ELEVATION, azim=CAMERA_AZIMUTH)
    extent = max(
        float(abs(x_values).max()),
        float(abs(y_values).max()),
        float(abs(z_values).max()),
    )
    axes.set_xlim(-extent, extent)
    axes.set_ylim(-extent, extent)
    axes.set_zlim(-extent, extent)
    axes.set_box_aspect((1, 1, 1))
    axes.set_axis_off()
    output.subplots_adjust(left=0, right=1, bottom=0, top=1)
    output.savefig(OUTPUT_PATH, transparent=True, bbox_inches="tight", pad_inches=0.02)
    plt.show()
    plt.close(output)


if __name__ == "__main__":
    main()
