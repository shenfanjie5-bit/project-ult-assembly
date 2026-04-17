"""Profile-specific exceptions."""


class ProfileError(Exception):
    """Base class for profile loading and validation errors."""


class ProfileNotFoundError(ProfileError):
    """Raised when a profile or service bundle file does not exist."""


class ProfileSchemaError(ProfileError):
    """Raised when profile or service bundle YAML fails schema validation."""


class ProfileConstraintError(ProfileError):
    """Raised when a profile violates a project-level hard constraint."""


class ProfileEnvMissingError(ProfileError):
    """Raised when required environment keys are missing during resolution."""
