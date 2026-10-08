"""Shared figure style for the solutions-manual notebooks.

THE RULE
    Static figures (the plots in the manuals) have a WHITE background.
    Animations have a BLACK background.
    Both use the neon / retro palette below.

Static figures -- importing applies the static style, so cells need no
plt.style.use(...):

    import sys; sys.path.insert(0, r"C:\\Users\\david\\Documents\\math")
    from plotstyle import C, FG, savefig

    ax.plot(x, y, color=C.cyan)              # or leave color out: the cycle is neon
    ax.vlines(a, 0, A, colors=FG)            # FG = text/axis colour (black)
    savefig(fig, "chap1ex1.3c.pdf")

Animations -- build AND save inside the block, which switches to the
animation style and back:

    from matplotlib.animation import FuncAnimation
    from plotstyle import animation_style, saveanim

    with animation_style() as A:             # A.C, A.FG, A.BG
        fig, ax = plt.subplots()
        line, = ax.plot([], [], color=A.C.magenta)
        anim = FuncAnimation(fig, update, frames=120, interval=33)
        saveanim(anim, "chap2wavepacket.mp4", fps=30)   # .mp4 is the default

Configuring colours: edit PALETTE (one entry per background) or ORDER (the
automatic colour cycle) below.  For one figure or animation, pass overrides:
animation_style(colors={'cyan': '#00FFFF'}).  After editing this file,
restart the kernel -- it is imported once.

savefig() and saveanim() write next to the notebook, then copy the file to the
matching folder of the LaTeX repository in WSL:

    Documents\\physics\\<book>\\chapN\\x.pdf  ->  ~/physics/<book>/chapN/x.pdf

latex-watch notices the new figure there and rebuilds the chapter and the
merged manual.  The same file lives in Documents\\math; it picks ~/math or
~/physics from the name of the folder it sits in.
"""

import shutil
import sys
import warnings
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
from cycler import cycler
import scienceplots  # noqa: F401 -- registers the 'science' styles

STATIC_THEME = "light"       # static figures: white background
ANIMATION_THEME = "dark"     # animations: black background

THEMES = {
    "dark":  dict(styles=['science', 'dark_background'], fg='white', bg='black'),
    "light": dict(styles=['science'],                    fg='black', bg='white'),
}

# Neon / retro.  Same names on both backgrounds.  On black the colours are full
# neon; on white they are the same hues stepped down just enough to keep 3:1
# contrast against the page.
PALETTE = {
    "dark": dict(
        cyan="#00F5FF", green="#39FF14", violet="#B44CFF", orange="#FF8A00",
        magenta="#FF2BD6", yellow="#FFE81F", blue="#3D8BFF", red="#FF3B5C",
    ),
    "light": dict(
        cyan="#0098B8", green="#16A300", violet="#8A2BE2", orange="#F05A00",
        magenta="#E6007E", yellow="#B08600", blue="#1F5BFF", red="#E8002D",
    ),
}

# Order of the automatic colour cycle (curves drawn without color=...).  Chosen
# so neighbours stay distinct for colour-blind readers on both backgrounds.
ORDER = ['cyan', 'green', 'violet', 'orange', 'magenta', 'yellow', 'blue', 'red']

WSL_HOME = Path(r"\\wsl.localhost\Ubuntu-22.04\home\cantorian_infinity")

# ffmpeg ships in the conda env but is only on PATH inside the Jupyter kernel.
_FFMPEG = Path(sys.prefix) / 'Library' / 'bin' / 'ffmpeg.exe'
if _FFMPEG.is_file():
    plt.rcParams['animation.ffmpeg_path'] = str(_FFMPEG)

_HERE = Path(__file__).resolve().parent          # Documents\physics or Documents\math
_LINUX_ROOT = WSL_HOME / _HERE.name.lower()      # ~/physics or ~/math (Windows may say "Physics")


def theme(name, colors=None):
    """Colours and matplotlib styles for theme `name`, with optional overrides."""
    t = THEMES[name]
    pal = {**PALETTE[name], **(colors or {})}
    rc = {'axes.prop_cycle': cycler(color=[pal[k] for k in ORDER])}
    return SimpleNamespace(name=name, FG=t['fg'], BG=t['bg'],
                           C=SimpleNamespace(**pal), styles=[*t['styles'], rc])


def tint(color, amount=0.5, toward=None):
    """`color` mixed `amount` of the way toward the background (white by default).

    A lighter fill that still reads as its hue, for histogram bars and the like
    under a curve.  Unlike alpha it works in EPS, which has no transparency.
    """
    from matplotlib.colors import to_rgb, to_hex
    base = to_rgb(toward or THEMES[STATIC_THEME]['bg'])
    return to_hex(tuple(c + (b - c) * amount for c, b in zip(to_rgb(color), base)))


def neon_cmap(theme_name=None, stops=('blue', 'violet', 'magenta', 'orange')):
    """Continuous neon colormap through the named PALETTE colours."""
    from matplotlib.colors import LinearSegmentedColormap
    pal = PALETTE[theme_name or STATIC_THEME]
    return LinearSegmentedColormap.from_list('neon', [pal[k] for k in stops])


_static = theme(STATIC_THEME)
THEME, FG, BG, C = _static.name, _static.FG, _static.BG, _static.C
plt.style.use(_static.styles)


@contextmanager
def animation_style(colors=None):
    """Switch to the animation style (black background) inside the block."""
    t = theme(ANIMATION_THEME, colors)
    with plt.style.context(t.styles):
        yield t


# Where the Windows tree does not mirror the Linux one 1:1: Windows prefix ->
# Linux prefix, relative to Documents\<root> and ~/<root>, '/'-separated.
PATH_MAP = {
    'ladata/parti': 'ladata',                    # Documents\math\ladata\parti\i1 -> ~/math/ladata/i1
    'fluidmechanics/chap3': 'fluidmechanics/chap3-code',
    'fluidmechanics/chap12': 'fluidmechanics/chap12-code',
}


def linux_dir(local_dir=None):
    """The WSL folder mirroring local_dir (default: the notebook's folder)."""
    local_dir = Path(local_dir or Path.cwd()).resolve()
    rel = local_dir.relative_to(_HERE).as_posix()    # <book>/chapN
    for win, lin in PATH_MAP.items():
        if rel.lower() == win or rel.lower().startswith(win + '/'):    # Windows ignores case
            rel = lin + rel[len(win):]
            break
    return _LINUX_ROOT / rel


def _mirror(local, linux_name=None):
    """Copy `local` into the WSL repo.  Warns and skips rather than failing.

    linux_name, if given, is the name (or sub-path, '/'-separated) to use
    inside the mirrored folder, for figures the manual knows by another name.
    """
    try:
        target_dir = linux_dir(local.parent)
    except ValueError:
        warnings.warn(f"{local.parent} is not under {_HERE}; not copied to WSL.")
        return
    try:
        if not target_dir.parent.is_dir():
            warnings.warn(f"No book folder {target_dir.parent} in WSL; not copied.")
            return
        target = target_dir / (linux_name or local.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local, target)
    except OSError as e:
        warnings.warn(f"Could not copy {local.name} to WSL: {e}")
        return
    print(f"saved {local.name} -> {target}")


def savefig(fig, name, mirror=True, linux_name=None, **kwargs):
    """Save fig as `name` next to the notebook, then copy it into the WSL repo.

    The format comes from the extension.  Extra keyword arguments go to
    fig.savefig.  The local save always happens; the copy is skipped, with a
    warning, if the notebook is outside this folder, the book has no folder in
    WSL, or WSL cannot be reached.  mirror=False skips the copy (for figures
    the manual does not use); linux_name renames it on the Linux side.
    """
    kwargs.setdefault('bbox_inches', 'tight')
    local = Path(name).resolve()
    fig.savefig(local, **kwargs)
    if mirror:
        _mirror(local, linux_name)
    return local


def saveanim(anim, name, fps=30, dpi=150, crf=18, mirror=True, linux_name=None,
             **kwargs):
    """Save a matplotlib animation; MP4 (H.264) by default, .gif if asked.

    A name without an extension gets .mp4.  crf is x264 quality (lower is
    better; 18 is visually lossless).  Call it inside the animation_style()
    block.  Extra keyword arguments go to anim.save.  Copied into the WSL
    repo like savefig.
    """
    from matplotlib import animation

    local = Path(name).resolve()
    if not local.suffix:
        local = local.with_suffix('.mp4')
    ext = local.suffix.lower()
    if ext == '.gif':
        writer = animation.PillowWriter(fps=fps)
    elif ext == '.mp4':
        if not animation.writers.is_available('ffmpeg'):
            raise RuntimeError("MP4 needs ffmpeg, which this environment does not have "
                               "(conda install -c conda-forge ffmpeg).")
        # yuv420p: plays everywhere (browsers, PowerPoint, phones), not just VLC.
        writer = animation.FFMpegWriter(fps=fps, codec='libx264',
                                        extra_args=['-pix_fmt', 'yuv420p', '-crf', str(crf)])
    else:
        raise ValueError(f"Unsupported animation format {ext!r}; use .mp4 or .gif.")
    fig = anim._fig
    kwargs.setdefault('savefig_kwargs', {'facecolor': fig.get_facecolor()})
    anim.save(local, writer=writer, dpi=dpi, **kwargs)
    if mirror:
        _mirror(local, linux_name)
    return local
