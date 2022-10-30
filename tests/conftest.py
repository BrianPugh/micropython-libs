from distutils import dir_util
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def data_path(tmp_path, request):
    """Safely access data related to test.

    Fixture responsible for searching a folder with the same name of test
    module and, if available, copying all contents to a temporary directory so
    tests can use them freely.
    """
    filename = Path(request.module.__file__)
    test_dir = filename.parent / filename.stem
    if test_dir.is_dir():
        dir_util.copy_tree(str(test_dir), str(tmp_path))

    return tmp_path


@pytest.fixture
def assert_array_equal(request):
    testname = request.node.name
    filename = Path(request.module.__file__)
    test_dir = filename.parent / filename.stem
    test_dir.mkdir(exist_ok=True)

    def _assert_array_equal(actual, index=0):
        expected_file = test_dir / f"{testname}_{index}_expected.npz"
        actual_file = test_dir / f"{testname}_{index}_actual.npz"

        actual = actual.astype(np.float16)
        np.savez_compressed(actual_file, data=actual)

        if not expected_file.exists():
            raise FileNotFoundError(
                f"{expected_file} does not exist! "
                "You can assert the generated file via:"
                f"\n\n    cp {actual_file} {expected_file} \n\n"
            )

        expected = np.load(expected_file)["data"]
        np.testing.assert_allclose(actual, expected, atol=0.0001)

    return _assert_array_equal
