# Placeholders

```
<!--wr:<name>[:<arg>][:<format>]-->  ...  <!--/wr-->
```

Whatever sits between the markers is discarded and rewritten.

## WakaTime metrics

All of these read the range set by [`time_range`](configuration.md), which
defaults to `all_time`.

| Metric | Argument | Produces |
| --- | --- | --- |
| `lang_hours` | language name | hours logged in that language |
| `lang_percent` | language name | share of total time |
| `lang_text` | language name | WakaTime's own phrasing, e.g. `892 hrs 29 mins` |
| `total_hours` | — | hours across all languages |
| `top_lang` | rank, 1-based (default `1`) | language name |
| `daily_average` | — | hours per day |
| `since` | — | first day of the range |

## GitHub metrics

| Metric | Argument | Produces |
| --- | --- | --- |
| `gh_followers` | — | follower count |
| `gh_repos` | — | number of public repositories |
| `gh_stars` | — | stars across all your public repositories |
| `gh_top_repo` | rank, 1-based (default `1`) | most-starred repository name |
| `gh_repo_stars` | `owner/repo` | stars on one repository |
| `gh_latest_release` | `owner/repo` | latest release tag |

## Formats

| Format | `892.5` becomes |
| --- | --- |
| `floor10` / `floor50` / `floor100` | `+890` / `+850` / `+800` |
| `int` | `892` |
| `1f` | `892.5` |
| `raw` | `892.4977...` |

A number with no format given renders as `int`, a string renders as `raw`.

Rounding down to a milestone is the point of `floor50`: the rendered value only
moves every 50 hours, so your README picks up a commit a few times a year
instead of every single day.

## The two-field rule

A placeholder with three fields is unambiguous *— `lang_hours:Python:1f` is a
metric, an argument and a format*. With **two** fields it is not, because
`top_lang:2` names a rank while `total_hours:1f` names a format.

The rule: **if the second field names a known format, it is the format.
Otherwise it is the argument.**

| Written | Argument | Format |
| --- | --- | --- |
| `total_hours:1f` | — | `1f` |
| `total_hours::1f` | — | `1f` |
| `top_lang:2` | `2` | — |
| `lang_hours:Python:1f` | `Python` | `1f` |

The explicit `metric::format` spelling, with an empty argument, always works and
is never ambiguous.

!!! note "This changed in 1.1.0"

    Before 1.1.0 the second field was always read as the argument, so a metric
    that takes none had no way to ask for a format and the request was dropped
    in silence *— i.e: `total_hours:1f` rendered `1920` where its author wanted
    `1920.4`*. If you worked around it with `::`, nothing breaks.

## Blocks

`activity_chart` renders the multi-line bar chart, so you do not need a second
action for it:

````markdown
<!--wr:activity_chart:last_7_days-->
```markdown
Total Time: 10 hrs

Markdown       4 hrs 30 mins    ⣿⣿⣿⣿⣿⣤⣀⣀⣀⣀   45.03 %
Python         2 hrs 1 min      ⣿⣿⣤⣀⣀⣀⣀⣀⣀⣀   20.30 %
```
<!--/wr-->
````

Its **argument is the range**, not a metric argument *— `last_7_days` above*.
Without one it uses `time_range`. It is the only placeholder that can name a
range, scalar metrics all read the run's `time_range`, because their second
field is already the argument.

Its appearance comes from the action inputs *— `blocks`, `lang_count`,
`ignored_languages`, `stop_at_other`, `show_total`, `show_time`, `code_lang` —*
not from the placeholder.

!!! warning "`last_7_days` is not your dashboard's last seven days:"

    The stats API window ends at midnight and excludes today, so it starts a day
    earlier than the range your dashboard shows. See
    [Matching WakaTime](matching-wakatime.md#the-last_7_days-window).

## Adding your own

Metrics, blocks and formats are three module-level registries *— `METRICS`,
`BLOCKS` and `FORMATTERS`*. Adding one is a single function plus a single entry,
never a change to the parser. See
[CONTRIBUTING.md](https://github.com/mmaachado/wakatime-readme/blob/master/.github/CONTRIBUTING.md).
