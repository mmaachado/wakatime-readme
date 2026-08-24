# Security Policy

## Supported versions

The project is pre-release. Until `v1.0.0` ships, only the latest commit on
`master` receives fixes.

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Use GitHub's private vulnerability reporting instead: go to the
[Security tab](https://github.com/mmaachado/wakatime-readme/security/advisories/new)
and open a draft advisory. You should get an acknowledgement within a few days.

Please include what you were running, what you observed, and the smallest
reproduction you can manage.

## Handling your WakaTime API key

This tool reads your key from the `WAKATIME_API_KEY` environment variable and
sends it only as an HTTP `Authorization` header. It is never placed in a URL
query string, written to a log line, or included in an exception message.

If you believe a key of yours has been exposed, revoke and regenerate it at
[wakatime.com/settings/api-key](https://wakatime.com/settings/api-key).
