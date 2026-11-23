# Matching WakaTime

If the numbers this tool publishes disagree with the ones on your WakaTime
profile, the cause is almost always the **keystroke timeout**, and the fix is
one line.

## What the keystroke timeout is

It is the maximum gap between keystrokes that WakaTime still counts as one
continuous stretch of coding. WakaTime's own FAQ puts it as *"the maximum time
allowed between durations when calculating your total coding activity for a
day."*

It does not create or destroy activity *— it decides how activity is grouped*. A
shorter timeout reports only the moments you were actually typing, a longer one
bridges the pauses between them. Code for two minutes, pause for thirteen, code
for one more, and a 15-minute timeout reports sixteen minutes while a 10-minute
timeout reports three.

Which means it moves totals **enormously**. It is not a rounding detail.

## Why your profile and your dashboard disagree

Here is the part that surprises people, straight from WakaTime's FAQ:

> Public profiles, leaderboards, and public badges always use the default
> 15-minute timeout, regardless of personal preference settings.

So there are two different numbers, and both are correct:

- Your **public profile, badges and leaderboards** always render at **15**.
- Your **signed-in dashboard** renders at whatever your account preference says.
- The **API** applies your account preference too, unless the request names a
  timeout explicitly.

If your account preference is not 15, your own dashboard has never agreed with
your own public profile. A README is a public artifact *— like the profile and
the badge —* so this tool **always sends the timeout explicitly and defaults to
15**, to match the surface a README is comparable to.

## What it looks like when it goes wrong

Measured on a real account whose preference was set to `5`, against a profile
page advertising `1,917 hrs 43 mins`:

| Request | Total | Python |
| --- | --- | --- |
| `stats/all_time?timeout=5` | 1,247.74 h | 622.25 h |
| `stats/all_time?timeout=15` | **1,917.73 h** | **897.50 h** |
| Profile page shows | 1,917 hrs 43 mins | ~890 hrs |

Every figure about a third low. Nothing looked broken *— `622 hrs 14 mins` of
Python is a perfectly plausible sentence to read in a README, which is exactly
why it went unnoticed*.

## Making everything agree

/// tab | Align your account (recommended)

Set your account preference to WakaTime's default so that your dashboard, your
profile, your badges and your README all count the same way.

1. Go to [wakatime.com/settings/preferences](https://wakatime.com/settings/preferences).
2. Find **keystroke timeout** and set it to **15 minutes**.
3. Save. Nothing else to change here *— `keystroke_timeout` already defaults
  to `15`*.

Your dashboard totals will jump, because they were the ones diverging from your
public profile all along.

///

/// tab | Match your dashboard instead

If you would rather every surface match your signed-in dashboard, tell the
action the value your account uses:

```yaml
- uses: mmaachado/wakatime-readme@v1
  with:
    wakatime_api_key: ${{ secrets.WAKATIME_API_KEY }}
    keystroke_timeout: '5'
```

Your README will then disagree with your public profile, because the profile
ignores the preference. That is a legitimate choice *— just make it knowingly*.

///

## Check it before you commit

`--dry-run` resolves every placeholder and writes nothing, so you can compare
against your profile in another tab:

```console
$ wakatime-readme --readme README.md --dry-run
$ wakatime-readme --readme README.md --dry-run --keystroke-timeout 5
```

Running it twice, once at each value, is the quickest way to see whether the
timeout is what is moving your numbers.

## A timeout WakaTime has not computed yet

WakaTime precomputes stats for the timeouts it expects *— the account preference
and the default 15*. Ask for anything else and the first request comes back
`202`, or `200` with `percent_calculated: 0`, while it works:

```
timeout=5    HTTP 200  cached=True   total=7.263h
timeout=10   HTTP 202  pct=0         total=0.000h
timeout=15   HTTP 200  cached=True   total=14.683h
timeout=20   HTTP 202  pct=0         total=0.000h
```

This is handled: the client retries within a 30-second budget and, if the answer
is still not final, it **gives up without writing**. See
[Behaviour](behaviour.md). An unusual `keystroke_timeout` simply costs you a
slower first run.

## The `last_7_days` window

One difference the keystroke timeout does **not** explain, and which no setting
will fix.

The stats API's `last_7_days` window ends at midnight and excludes today, so it
begins a day earlier than the range your dashboard shows. The two cover
genuinely different weeks:

| Source | Window | Total |
| --- | --- | --- |
| `stats/last_7_days` | Aug 24 – Aug 30, today excluded | 7 hrs 15 mins |
| Dashboard "Last 7 Days" | Aug 25 – Aug 31, today included | 4 hrs 39 mins |

Expect `activity_chart:last_7_days` to differ from the headline number on your
dashboard for this reason alone. `all_time` has no such discrepancy.

## Still not matching?

- Compare `lang_text` against your profile rather than `lang_hours`. It returns
  WakaTime's own phrasing, so any difference is in the data and not in
  formatting.
- Check the run's log. A refusal to write is reported as a warning naming the
  keystroke timeout and how long it waited.
- Remember that `time_range` defaults to `all_time`, while your dashboard opens
  on Last 7 Days.
