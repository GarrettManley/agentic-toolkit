"""End-to-end probe for a Cloudflare Email Routing forwarding address."""

import truststore

# uv-managed CPython ships without access to the Windows certificate store; route every
# TLS verification in this package (DoH, Resend, IMAP, SMTP) through the OS trust store.
truststore.inject_into_ssl()
