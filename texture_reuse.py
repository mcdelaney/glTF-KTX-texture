"""
Helpers for reusing imported external KTX2 texture references during export.
"""

import os


KTX2_SOURCE_URI_PROP = "ktx2_source_uri"
KTX2_SOURCE_PATH_PROP = "ktx2_source_path"


def is_external_ktx2_uri(uri):
    """Return True when the URI points at an external file we can reference again."""
    return isinstance(uri, str) and uri != "" and not uri.startswith("data:")


def capture_import_metadata(uri, gltf_filename):
    """
    Build reusable source metadata for an imported KTX2 image.

    Returns None for embedded/data-URI sources because there is no stable external file
    to reference during export.
    """
    if not is_external_ktx2_uri(uri):
        return None

    metadata = {
        KTX2_SOURCE_URI_PROP: uri,
    }

    if gltf_filename:
        metadata[KTX2_SOURCE_PATH_PROP] = os.path.normpath(
            os.path.join(os.path.dirname(gltf_filename), uri)
        )

    return metadata


def get_image_metadata(blender_image):
    """Read reusable KTX2 metadata from a Blender image custom property bag."""
    uri = blender_image.get(KTX2_SOURCE_URI_PROP)
    if not is_external_ktx2_uri(uri):
        return None

    source_path = blender_image.get(KTX2_SOURCE_PATH_PROP)
    if not isinstance(source_path, str) or source_path == "":
        source_path = None

    return {
        "uri": uri,
        "path": source_path,
    }


def resolve_export_uri(source_uri, source_path, export_filepath):
    """
    Resolve the URI to write into the re-exported glTF.

    When both the original absolute path and the new export path are known, try to keep the
    reference valid by re-basing it relative to the new export directory.
    """
    if source_path and export_filepath:
        export_dir = os.path.dirname(os.path.abspath(export_filepath))
        try:
            source_uri = os.path.relpath(source_path, export_dir)
        except ValueError:
            source_uri = source_uri or os.path.basename(source_path)

    if not source_uri:
        return None

    return source_uri.replace("\\", "/")
