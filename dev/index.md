# wakatime-readme

Dev metrics with [WakaTime](https://wakatime.com) for your `README.md`.

A GitHub Action, and a standalone CLI, that fills **named placeholders** in a
Markdown file with live numbers from the WakaTime API and the GitHub API.

```markdown
I'm a prolific Python developer with <!--wr:lang_hours:Python:floor50-->+850<!--/wr--> hours.
```

## Why it exists

Other solutions rewrite one fixed block with a bar chart of your recent
activity. What they cannot do is put a single number in the middle of a
sentence *— and that is what most profile READMEs actually want*.

This project does both. It injects a value inline, anywhere in your prose, *and*
renders the bar chart, so it can take over the whole job rather than sit beside
another action.

## What makes it different

- **No checkout, no commit step.** The file is read and written through the
  **GitHub Contents API**. Your workflow is one `uses:` block.
- **Commits land Verified.** `GITHUB_TOKEN` is a bot token, and GitHub signs
  what bots commit through the REST API.
- **Zero runtime dependencies.** Standard library only, so the Docker image
  stays small and the supply chain stays empty.
- **It never writes a number it does not believe.** WakaTime computes long
  ranges lazily, if the answer is not final, the file is left alone.

## Start here

- [Getting started](getting-started.md) - a working workflow in one step.
- [Placeholders](placeholders.md) - every metric, format and block.
- [Configuration](configuration.md) - every input and its default.
- [Matching WakaTime](matching-wakatime.md) - **read this** if the numbers in
  your README disagree with the ones on your WakaTime profile.
- [Behaviour](behaviour.md) - exit codes and the guarantees behind them.

!!! warning "If your numbers look too low:"

    A README published without the right **keystroke timeout** can read about a
    third below what your WakaTime profile advertises *— 622 hours of Python
    where the profile says 898*. It is a one-line fix, explained in
    [Matching WakaTime](matching-wakatime.md).
