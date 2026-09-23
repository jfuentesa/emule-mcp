class EMuleMCPError(Exception):
    """Base class for errors raised by this server."""


class ConfigError(EMuleMCPError):
    """The server configuration is missing or invalid."""


class EMuleOfflineError(EMuleMCPError):
    """The eMule WebServer cannot be reached."""


class AuthenticationError(EMuleMCPError):
    """The eMule WebServer rejected the WebServer password."""


class ParseError(EMuleMCPError):
    """A WebServer response could not be parsed."""


class InvalidLinkError(EMuleMCPError):
    """An eD2k link is missing or malformed."""
