# wakatime-readme

Dev metrics with [WakaTime](https://wakatime.com) for your README.md

**[Documentation](https://mmaachado.github.io/wakatime-readme/)** ·
[Placeholders](https://mmaachado.github.io/wakatime-readme/latest/placeholders/) ·
[Configuration](https://mmaachado.github.io/wakatime-readme/latest/configuration/) ·

## Why

Other solutions rewrite one fixed block with a bar chart of your recent activity. What they cannot do is put a single number in the middle of a sentence:

```markdown
I'm a prolific Python developer with <!--wr:lang_hours:Python:floor50-->+850<!--/wr--> hours.
```

That is the gap this fills. It also renders the bar chart itself, so it can take over the whole job rather than sitting beside it.

## Usage

```yaml
permissions:
  contents: write

jobs:
  update-readme:
    runs-on: ubuntu-latest
    steps:
      - uses: mmaachado/wakatime-readme@v1
        with:
          wakatime_api_key: ${{ secrets.WAKATIME_API_KEY }}
```

That is the whole workflow. No `actions/checkout`, no commit step. The file is
read and written through the GitHub Contents API, and because `github_token`
defaults to the workflow's own token, the commit lands **Verified**

Get your key from [wakatime.com/api-key](https://wakatime.com/api-key) and store
it as a repository secret. It is only ever sent as an `Authorization` header,
never in a URL

A complete workflow and a profile README wired up to every placeholder are in
[`examples/`](examples/). Full reference — every metric, format, block and input
— lives in the
[documentation](https://mmaachado.github.io/wakatime-readme/)

### As a CLI

```console
$ export WAKATIME_API_KEY=waka_...
$ uvx wakatime-readme --readme README.md --dry-run
```

`--dry-run` prints what each placeholder would resolve to and touches nothing.
Without `--repo`, the CLI reads and writes your local file directly

## Behaviour worth knowing

- **All or nothing.** Every placeholder resolves in memory before anything is
  written, and it all lands in one commit. A broken placeholder leaves the file
  untouched rather than half-filled;
- **Never guesses.** WakaTime recomputes long ranges lazily. The tool retries
  for up to 30 seconds, then gives up without writing — a stale README beats a
  wrong one — and says so with exit `2`;
- **Only fetches what you use.** No `gh_*` placeholder, no call to GitHub; no
  WakaTime placeholder, no call to WakaTime. You are never asked for a
  credential you do not need;
- **Counts the way your profile counts.** WakaTime's keystroke timeout changes
  totals by a third, and its public pages always render at `15` regardless of
  your account preference. This tool sends the value explicitly and defaults to
  `15`. If your numbers look too low, read
  [Matching WakaTime](https://mmaachado.github.io/wakatime-readme/latest/matching-wakatime/)

The rest, including exit codes and the `last_7_days` window, is in
[Behaviour](https://mmaachado.github.io/wakatime-readme/latest/behaviour/)

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md). Bug reports and feature requests
are welcome in [issues](https://github.com/mmaachado/wakatime-readme/issues)

## License

Licensed under the [MIT](LICENSE) license
