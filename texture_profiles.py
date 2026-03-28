"""
Helpers for resolving per-texture export settings.

This module is intentionally Blender-free so it can be unit tested.
"""

ROLE_BASECOLOR = "basecolor"
ROLE_NORMAL = "normal"
ROLE_ORM = "orm"
ROLE_OTHER = "other"

EXPORT_DEFAULTS_VERSION = 1

LEGACY_FORMAT_STATE = {
    "target_format": "BASISU",
    "target_type": "Auto",
    "target_oetf": "Auto",
    "downsample_factor": 1,
    "basisu_mode": "Auto",
    "astc_block_size": "6x6",
}

ROLE_DEFAULTS = {
    ROLE_BASECOLOR: {"target_format": "BCN", "bc_format": "BC7"},
    ROLE_NORMAL: {"target_format": "BCN", "bc_format": "BC5"},
    ROLE_ORM: {"target_format": "BCN", "bc_format": "BC7"},
    ROLE_OTHER: {"target_format": "BASISU"},
}

AUTO_TARGET_TYPES = {
    1: "R",
    2: "RG",
    3: "RGB",
    4: "RGBA",
}

BC_FORMAT_TARGET_TYPES = {
    "BC1": {"RGB"},
    "BC3": {"RGB", "RGBA"},
    "BC4": {"R"},
    "BC5": {"RG"},
    "BC7": {"RGB", "RGBA"},
}


def detect_texture_role(socket_names):
    names = set(socket_names)
    if "Base Color" in names:
        return ROLE_BASECOLOR
    if "Normal" in names:
        return ROLE_NORMAL
    if names & {"Metallic", "Roughness", "Occlusion"}:
        return ROLE_ORM
    return ROLE_OTHER


def default_oetf(socket_names):
    if set(socket_names) & {"Base Color", "Emission"}:
        return "srgb"
    return "linear"


def default_basisu_mode(socket_names):
    if set(socket_names) & {"Base Color", "Emission"}:
        return "ETC1S"
    return "UASTC"


def resolve_target_type(channels, requested_target_type, target_format, bc_format):
    if requested_target_type != "Auto":
        return requested_target_type

    if target_format == "BCN":
        if bc_format == "BC4":
            return "R"
        if bc_format == "BC5":
            return "RG"

    return AUTO_TARGET_TYPES.get(channels, "RGBA")


def validate_bcn_selection(target_format, target_type, bc_format):
    if target_format != "BCN":
        return None

    allowed = BC_FORMAT_TARGET_TYPES.get(bc_format)
    if not allowed:
        return f"Unsupported BC format '{bc_format}'."

    if target_type not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        return f"{bc_format} requires target channels {allowed_list}, got {target_type}."

    return None


def resolve_texture_settings(socket_names, channels, format_state):
    role = detect_texture_role(socket_names)
    target_format = format_state["target_format"]
    bc_format = format_state.get("bc_format", "BC7")

    oetf = default_oetf(socket_names)
    if format_state["target_oetf"] != "Auto":
        oetf = format_state["target_oetf"]

    compression_mode = default_basisu_mode(socket_names)
    if format_state["basisu_mode"] != "Auto":
        compression_mode = format_state["basisu_mode"]

    target_type = resolve_target_type(
        channels,
        format_state["target_type"],
        target_format,
        bc_format,
    )

    error = validate_bcn_selection(target_format, target_type, bc_format)

    return {
        "role": role,
        "target_format": target_format,
        "bc_format": bc_format,
        "oetf": oetf,
        "compression_mode": compression_mode,
        "target_type": target_type,
        "error": error,
    }


def get_role_defaults(role):
    return ROLE_DEFAULTS[role]


def is_legacy_format_state(format_state):
    return (
        format_state.get("target_format") == LEGACY_FORMAT_STATE["target_format"]
        and format_state.get("target_type") == LEGACY_FORMAT_STATE["target_type"]
        and format_state.get("target_oetf") == LEGACY_FORMAT_STATE["target_oetf"]
        and format_state.get("downsample_factor") == LEGACY_FORMAT_STATE["downsample_factor"]
        and format_state.get("basisu_mode") == LEGACY_FORMAT_STATE["basisu_mode"]
        and format_state.get("astc_block_size") == LEGACY_FORMAT_STATE["astc_block_size"]
    )
