import contextlib
import os
import platform
import shutil
import tempfile

# noinspection PyPackageRequirements
from pathlib import Path

# noinspection PyPackageRequirements
import pytest

from paquo.images import ImageProvider, QuPathProjectImageEntry, QuPathImageType
from paquo.projects import QuPathProject


@pytest.fixture(scope='function')
def new_project(tmp_path):
    yield QuPathProject(tmp_path / "paquo-project")


def test_project_instance():
    with tempfile.TemporaryDirectory(prefix='paquo-') as tmpdir:
        q = QuPathProject(tmpdir)
        repr(q)
        q.save()


def test_project_create_no_dir():
    with tempfile.TemporaryDirectory(prefix='paquo-') as tmpdir:
        project_path = Path(tmpdir) / "new_project"
        q = QuPathProject(project_path)
        q.save()


def test_project_creation_input_error(tmp_path):

    p = Path('.')

    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        QuPathProject(p, image_provider=object())

    with pytest.raises(ValueError):
        QuPathProject(p / 'myproject.proj')  # needs .qpproj

    with pytest.raises(FileNotFoundError):
        QuPathProject(p / 'myproject.qpproj', create=False)

    with open(p / 'should-not-be-here', 'w') as f:
        f.write('project directories need to be empty')
    with pytest.raises(ValueError):
        QuPathProject(p)


def test_project_open_with_filename(new_project):
    new_project.save()
    # this points to path/project.qpproj
    proj_fn = new_project.path
    QuPathProject(proj_fn, create=False)


def test_project_name(tmp_path):
    p = Path(tmp_path) / "my_project_123"
    p.mkdir()
    qp = QuPathProject(p)
    assert qp.name == "my_project_123"


def test_project_uri(new_project):
    assert new_project.uri.startswith("file:")
    assert new_project.uri.endswith(".qpproj")
    # uri_previous is None for empty projects
    assert new_project.uri_previous is None


def test_project_save_and_path(new_project):
    assert not new_project.path.is_file()
    new_project.save()
    assert new_project.path.is_file()


def test_project_version(new_project):
    from paquo.java import GeneralTools
    new_project.save()
    qp_version = str(GeneralTools.getVersion())
    assert new_project.version == qp_version

    with QuPathProject(new_project.path, create=False) as qp:
        assert qp.version == qp_version


def test_project_add_path_classes(new_project):
    from paquo.classes import QuPathPathClass

    names = {'a', 'b', 'c'}
    new_project.path_classes = map(QuPathPathClass.create, names)

    assert len(new_project.path_classes) == 3
    assert set(c.name for c in new_project.path_classes) == names


def test_download_svs(svs_small):
    assert svs_small.is_file()


def test_timestamps(new_project):
    assert new_project.timestamp_creation > 0
    assert new_project.timestamp_modification > 0


def test_project_add_image(new_project, svs_small):
    with pytest.raises(ValueError):
        # can't add images by instantiating them
        QuPathProjectImageEntry(svs_small)

    entry = new_project.add_image(svs_small)
    assert (Path(entry.entry_path) / "thumbnail.jpg").is_file()

    assert len(new_project.images) == 1
    assert entry in new_project.images
    assert object() not in new_project.images


def test_project_add_image_with_type(new_project, svs_small):
    t = QuPathImageType.BRIGHTFIELD_H_DAB
    entry = new_project.add_image(svs_small, image_type=t)
    assert entry.image_type == t


def test_project_add_unsupported_image(new_project, tmp_path):
    image = Path(tmp_path) / "unsupported.image"
    with open(image, "w") as f:
        f.write("very unsupported image")

    with pytest.raises(IOError):
        new_project.add_image(image)


def test_project_image_slicing(new_project):
    _ = new_project.images[slice(None, None, None)]


def test_project_image_repr(new_project):
    assert repr(new_project.images)


def test_project_add_image_incorrect_path(new_project):
    with pytest.raises(FileNotFoundError):
        new_project.add_image("i-do-not-exist.svs")


def test_project_save_image_data(new_project, svs_small):
    from paquo.pathobjects import QuPathPathAnnotationObject
    from shapely.geometry import Point
    entry = new_project.add_image(svs_small)
    entry.hierarchy.annotations.add(
        QuPathPathAnnotationObject.from_shapely(
            Point(1, 2)
        )
    )
    new_project.save()
    assert (entry.entry_path / "data.qpdata").is_file()


def test_project_delete_image_file_when_opened(new_project, svs_small):
    # prepare new image to be deleted
    new_svs_small = new_project.path.parent / f"image_be_gone{svs_small.suffix}"
    shutil.copy(svs_small, new_svs_small)

    entry = new_project.add_image(new_svs_small)
    assert entry.is_readable()

    if platform.system() == "Windows":
        # NOTE: on windows because you can't delete files that have open
        #   file handles. In this test we're deleting the file opened by
        #   the ImageServer on the java side. (this is happening
        #   implicitly when calling is_readable() because the java
        #   implementation of is_readable() loads the ImageData which
        #   creates an instance of an ImageServer)
        cm = pytest.raises(PermissionError)
    else:
        cm = contextlib.nullcontext()

    with cm:
        os.unlink(new_svs_small)


@pytest.mark.xfail(platform.system() == "Windows", reason="file handles don't get closed by qupath?")
def test_project_image_uri_update(tmp_path, svs_small):

    project_path = tmp_path / "paquo-project"
    new_svs_small = tmp_path / "images" / f"image_be_gone{svs_small.suffix}"
    new_svs_small.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(svs_small, new_svs_small)
    assert new_svs_small.is_file()

    # create a project
    with QuPathProject(project_path, create=True) as qp:
        entry = qp.add_image(new_svs_small)
        assert entry.is_readable()
        assert all(qp.is_readable().values())

    # cleanup
    del entry
    del qp

    # remove image
    os.unlink(new_svs_small)

    # reload the project
    with QuPathProject(project_path, create=False) as qp:
        entry, = qp.images
        assert not entry.is_readable()
        assert not all(qp.is_readable().values())

        # create mapping for uris
        uri2uri = {
            entry.uri: ImageProvider.uri_from_path(svs_small)
        }
        # update the uris
        qp.update_image_paths(uri2uri=uri2uri)

        # test that entry can be read
        assert entry.is_readable()
        assert all(qp.is_readable().values())
