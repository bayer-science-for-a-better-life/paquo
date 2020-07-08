import os
import sys
from pathlib import Path
from typing import Tuple, Optional, List


def conda_env_prefix() -> Optional[Path]:
    prefix = os.environ.get('CONDA_PREFIX')
    if prefix:
        return Path(prefix)
    return None

# N.B. we could depend on conda itself and depend on its API, but we will just use paths here


def qupath_conda_paths() -> Optional[Tuple[Path, Path, Path, List[str]]]:
    """
    Finds qupath and relevant JRE installation paths in the current conda environment

    Returns a tuple (app_dir, runtine_dir, jvm_path, jvm_options), or None if not found.
    """

    conda_prefix = conda_env_prefix()
    if conda_prefix:
        if sys.platform == "linux" or sys.platform == "linux2":
            app_dir = conda_prefix / 'opt' / 'QuPath' / 'lib' / 'app'
            runtime_dir = conda_prefix / 'opt' / 'QuPath' / 'lib' / 'runtime'
            jvm_path = runtime_dir / 'lib' / 'server' / 'libjvm.so'
            jvm_options = []
        elif sys.platform == "darwin":
            qupath_dir = conda_prefix / 'bin' / 'QuPath.app'
            app_dir = qupath_dir / 'Contents' / 'app'
            runtime_dir = qupath_dir / 'Contents' / 'runtime' / 'Contents' / 'Home'
            jvm_path = runtime_dir / 'lib' / 'server' / 'libjvm.dylib'
            jvm_options = [
                f'-Djava.library.path={app_dir}:{qupath_dir}/Contents/MacOS',
                f'-Djava.launcher.path={qupath_dir}/Contents/MacOS',
                # '-Djavafx.macosx.embedded=true',
                # '-XstartOnFirstThread',
                # '-Djava.awt.headless=true',
                # '-XX:MaxRAMPercentage=50',
            ]
        elif sys.platform == "win32":
            app_dir = conda_prefix / 'Library' / 'QuPath' / 'app'
            runtime_dir = conda_prefix / 'Library' / 'QuPath' / 'runtime'
            jvm_path = None  # TODO
            jvm_options = []
        else:
            raise Exception('Unknown platform {}'.format(sys.platform))
        if app_dir.is_dir() and runtime_dir.is_dir():
            return app_dir, runtime_dir, jvm_path, jvm_options
    return None


def find_qupath() -> Optional[Tuple[Path, Path, Path, List[str]]]:
    """
    Finds current qupath and relevant JRE installation paths, returning a tuple (app_dir, runtine_dir).
    """
    # FIXME: merge this with qupath_conda_paths
    app_dir, runtime_dir, jvm_path, jvm_options = qupath_conda_paths()
    assert app_dir.is_dir()
    assert runtime_dir.is_dir()
    assert jvm_path.is_file()
    return app_dir, runtime_dir, jvm_path, jvm_options