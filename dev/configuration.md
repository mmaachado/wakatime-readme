# Configuration

Every action input has a command-line equivalent. Inputs are also read from the
plain environment, so `WAKATIME_API_KEY` works as well as
`INPUT_WAKATIME_API_KEY`.

Precedence is explicit argument, then action input, then plain environment
variable, then default.

## Credentials and target

| Input | CLI flag | Default | What it does |
| --- | --- | --- | --- |
| `wakatime_api_key` | `WAKATIME_API_KEY` | — | Your key from [wakatime.com/api-key](https://wakatime.com/api-key). Only needed if the file uses WakaTime placeholders. |
| `github_token` | `GITHUB_TOKEN` | `${{ github.token }}` | Reads metrics and commits the result. The default is the workflow's own token, which GitHub signs, so the commit lands Verified. |
| `repository` | `--repo` | `${{ github.repository }}` | Repository holding the file, as `owner/name`. Without it, the CLI edits the local file instead. |
| `readme_path` | `--readme` | `README.md` | Path to the file, relative to the repository root. |
| `branch` | `--branch` | repository default | Branch to commit to. |
| `username` | `--username` | owner of `repository` | Account the GitHub metrics describe. Needed because the workflow token belongs to a bot, not to a person. |

## WakaTime

| Input | CLI flag | Default | What it does |
| --- | --- | --- | --- |
| `time_range` | `--range` | `all_time` | Range for placeholders that do not name one: `all_time`, `last_7_days`, `last_30_days`, `last_6_months`, `last_year`. |
| `keystroke_timeout` | `--keystroke-timeout` | `15` | Minutes of pause that still count as coding. **See [Matching WakaTime](matching-wakatime.md).** |
| `retries` | `--retries` | `6` | Attempts while WakaTime computes a range, spending at most 30 seconds asleep between them. |

## Failure behaviour

| Input | CLI flag | Default | What it does |
| --- | --- | --- | --- |
| `strict` | `--strict` | `false` | Exit `2` when an API could not be reached. Off by default so a scheduled run does not fail over a brief outage. Stale WakaTime data fails regardless *— see [Behaviour](behaviour.md)*. |
| `dry_run` | `--dry-run` | `false` | Report what would change and write nothing. |

## The commit

| Input | CLI flag | Default | What it does |
| --- | --- | --- | --- |
| `commit_message` | `--message` | `chore: refresh README metrics` | Message for the commit. |
| `committer_name` | `--committer-name` | — | Committer name. Both name and email, or neither. |
| `committer_email` | `--committer-email` | — | Committer email. |
| `author_name` | `--author-name` | — | Author name. Both name and email, or neither. |
| `author_email` | `--author-email` | — | Author email. |

## The activity chart

These configure `activity_chart`.

| Input | CLI flag | Default | What it does |
| --- | --- | --- | --- |
| `blocks` | `--blocks` | `⣀⣄⣤⣦⣶⣷⣿` | Characters used to draw the bar, empty to full. At least two. |
| `code_lang` | `--code-lang` | `markdown` | Language tag on the chart's code fence. Empty for no fence. |
| `lang_count` | `--lang-count` | `5` | How many languages the chart lists. |
| `ignored_languages` | `--ignore` | — | Space-separated language names to leave out. |
| `stop_at_other` | `--stop-at-other` | `false` | Stop the chart when the `Other` bucket is reached. |
| `show_time` | `--show-time` | `true` | Include the time column. |
| `show_total` | `--show-total` | `true` | Include the `Total Time:` header. |

## Endpoints

| Input | CLI flag | Default | What it does |
| --- | --- | --- | --- |
| `api_base_url` | `--wakatime-url` | `https://wakatime.com/api/v1` | For WakaTime-compatible services such as Wakapi or Hakatime. |
| `github_api_url` | `--github-url` | `https://api.github.com` | For GitHub Enterprise. |

## Boolean flags on the command line

Every boolean input has a negative form, so a value set in the environment can
be turned off for one run:

```console
$ wakatime-readme --readme README.md --no-show-total --no-strict
```
