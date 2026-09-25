from studio.version import APP_NAME, APP_VERSION


def test_version_is_reset_to_v1():
    assert APP_NAME == "4cut Local Comic Studio"
    assert APP_VERSION == "v1.2.2"
