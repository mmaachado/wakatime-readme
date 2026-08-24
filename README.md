# wakatime-readme

dev metrics with [WakaTime](https://wakatime.com) for your README.md

> Warning
>
> **Status: pre-release.** The v0.1.0 contract is specified and the packaging is
> in place, but the implementation has not landed yet. There is no published
> release or container image, so the usage below does not work today. Watch the
> repository for `v1`

## Why

Other's solution rewrites one fixed block with a bar chart of your recent activity. What it cannot do is put a single number in the middle of a sentence:

```markdown
I'm a prolific Python developer with <!--wr:lang_hours:Python:floor50-->+850<!--/wr--> hours.
```

That is the gap this fills. It also renders the bar chart itself, so it can take
over the whole job rather than sitting beside it

## Placeholders

```
<!--wr:<name>[:<arg>][:<format>]-->  ...  <!--/wr-->
```

Whatever sits between the markers is replaced

### WakaTime metrics

| Metric          | Argument                    | Produces                                        |
| --------------- | --------------------------- | ----------------------------------------------- |
| `lang_hours`    | language name               | hours logged in that language                   |
| `lang_percent`  | language name               | share of total time                             |
| `lang_text`     | language name               | WakaTime's own phrasing, e.g. `892 hrs 29 mins` |
| `total_hours`   | -                           | hours across all languages                      |
| `top_lang`      | rank, 1-based (default `1`) | language name                                   |
| `daily_average` | -                           | hours per day                                   |
| `since`         | -                           | first day of the range                          |

### GitHub metrics

| Metric              | Argument                    | Produces                                  |
| ------------------- | --------------------------- | ----------------------------------------- |
| `gh_followers`      | -                           | follower count                            |
| `gh_repos`          | -                           | number of public repositories             |
| `gh_stars`          | -                           | stars across all your public repositories |
| `gh_top_repo`       | rank, 1-based (default `1`) | most-starred repository name              |
| `gh_repo_stars`     | `owner/repo`                | stars on one repository                   |
| `gh_latest_release` | `owner/repo`                | latest release tag                        |

### Formats

| Format                             | `892.5` becomes          |
| ---------------------------------- | ------------------------ |
| `floor10` / `floor50` / `floor100` | `+890` / `+850` / `+800` |
| `int`                              | `892`                    |
| `1f`                               | `892.5`                  |
| `raw`                              | `892.4977...`            |

Rounding down to a milestone is the point of `floor50`: the rendered value only
changes every 50 hours, so your README picks up a commit a few times a year
instead of every single day

### Blocks

`activity_chart` renders the multi-line bar chart, so you do not need a second
action for it:

````markdown
<!--wr:activity_chart:last_7_days-->

```markdown
Total Time: 10 hrs

Markdown 4 hrs 30 mins ⣿⣿⣿⣿⣿⣤⣀⣀⣀⣀ 45.03 %
Python 2 hrs 1 min ⣿⣿⣤⣀⣀⣀⣀⣀⣀⣀ 20.30 %
```

<!--/wr-->
````

Its appearance is configured through the action inputs (`blocks`, `lang_count`,
`ignored_languages`, `stop_at_other`, `show_total`, `show_time`, `code_lang`),
which are named after their `waka-readme` equivalents so migrating is a copy of
your existing configuration

## Usage

### As a GitHub Action

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
read and written through the GitHub Contents API. `github_token` defaults to the
workflow's own token, so there is nothing else to wire up

Get your WakaTime key from [wakatime.com/api-key](https://wakatime.com/api-key)
and store it as a repository secret. It is only ever sent as an `Authorization`
header, never in a URL

To write to a **different** repository — a profile README from another repo, say
— pass a personal access token with `contents: write` as `github_token` and set
`repository`. Note that a PAT produces an ordinary commit; the verified signature
below only comes with the default token

### As a CLI

```console
$ export WAKATIME_API_KEY=waka_...
$ uvx wakatime-readme --readme README.md --dry-run
```

`--dry-run` prints what each placeholder would resolve to and touches nothing.
Without `--repo`, the CLI reads and writes your local file directly

## Behaviour worth knowing

- **Commits land Verified.** `GITHUB_TOKEN` is a bot token, and GitHub signs
  commits that bots make through the REST API. Your profile history stays clean.
- **All or nothing.** Every placeholder is resolved in memory before anything is
  written, and everything lands in a single commit. One bad placeholder leaves
  the file untouched rather than half-filled;
- **Only fetches what you use.** A file with no `gh_*` placeholder never calls
  GitHub for metrics; a file with no WakaTime placeholder never calls WakaTime.
  You are not asked for credentials you do not need;
- **Never guesses.** WakaTime recomputes long ranges lazily and answers `202` or
  `is_up_to_date: false` in the meantime. The tool retries, then gives up without
  writing. A stale README beats a wrong one;
- **Quiet when nothing changed.** If the output matches what is already in the
  file, no write happens, so there is no empty commit;
- **Green by default.** A transient API outage exits `0` with a warning, so a
  daily cron does not go red. Pass `--strict` to make it exit `2` instead;

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and feature requests are
welcome in [issues](https://github.com/mmaachado/wakatime-readme/issues)

## License

Licensed under the [MIT](LICENSE) license
