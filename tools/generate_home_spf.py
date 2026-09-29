"""Generate the animated SPF preview used on the home page."""

from matplotlib.animation import FuncAnimation, PillowWriter
from pathlib import Path

import numpy as np
import matplotlib
from matplotlib import cm
from matplotlib.colors import Normalize

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from PyMieSimX.gui.computation import build_single_figure


OUTPUT_PATH = Path(__file__).parents[1] / "PyMieSimX" / "gui" / "assets" / "home-spf-radial.gif"
CAMERA_ELEVATION = 18
FRAME_COUNT = 48


def main() -> None:
    figure, _summary = build_single_figure(
        source_type="Gaussian",
        source_values={},
        scatterer_type="Sphere",
        scatterer_values={"diameter": "100"},
        representation="spf",
        projection="3d_radial",
        sampling=120,
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
    surface_colors = cm.viridis(Normalize(vmin=lower, vmax=upper)(values))
    background_color = "#f5f8fc"

    output = plt.figure(figsize=(5.5, 5.5), dpi=110, facecolor=background_color)
    axes = output.add_subplot(111, projection="3d")
    axes.set_facecolor(background_color)
    axes.plot_surface(
        x_values,
        y_values,
        z_values,
        facecolors=surface_colors,
        rcount=60,
        ccount=60,
        edgecolor="#000000",
        linewidth=0.22,
        antialiased=True,
        shade=False,
    )
    axes.set_proj_type("ortho")
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

    def rotate(frame: int):
        angle = 2.0 * np.pi * frame / FRAME_COUNT
        elevation = CAMERA_ELEVATION + 12.0 * np.sin(angle)
        axes.view_init(elev=elevation, azim=360.0 * frame / FRAME_COUNT)
        return (axes,)

    animation = FuncAnimation(output, rotate, frames=FRAME_COUNT, interval=1000 / 24, blit=False)
    animation.save(
        OUTPUT_PATH,
        writer=PillowWriter(fps=24),
        savefig_kwargs={"facecolor": background_color},
    )
    plt.close(output)


if __name__ == "__main__":
    main()
