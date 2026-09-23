"""Generate the static high-resolution SPF preview used on the home page."""

from pathlib import Path

from matplotlib import cm
from matplotlib.colors import Normalize
import matplotlib.pyplot as plt

from PyMieSimX.gui.computation import build_single_figure


OUTPUT_PATH = Path(__file__).parents[1] / "PyMieSimX" / "gui" / "assets" / "home-spf-radial.png"


def main() -> None:
    figure, _summary = build_single_figure(
        source_type="Gaussian",
        source_values={},
        scatterer_type="Sphere",
        scatterer_values={},
        representation="spf",
        projection="3d_radial",
        sampling=300,
    )
    trace = figure.data[0]
    x_values, y_values, z_values = trace.x, trace.y, trace.z
    intensity = trace.surfacecolor
    colors = cm.viridis(
        Normalize(vmin=float(intensity.min()), vmax=float(intensity.max()))(intensity)
    )

    output = plt.figure(figsize=(8, 5), dpi=240, facecolor="none")
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
        shade=True,
    )
    axes.set_proj_type("ortho")
    axes.view_init(elev=24, azim=-52)
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
    plt.close(output)


if __name__ == "__main__":
    main()
