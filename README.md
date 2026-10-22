# Pokémon GO personal calendar

This repository builds a subscribable `.ics` calendar from the current ScrapedDuck event feed (which mirrors Leek Duck). The workflow refreshes it daily and can also be run manually.

## Included events

Edit `included_event_types` in `config.json` to change the selection. The default includes general `event`s, `community-day`, and the larger `pokemon-go-tour`, `pokemon-go-fest`, and `wild-area` events. Types such as `raid-day`, `raid-hour`, `raid-battles`, `go-battle-league`, and `pokemon-spotlight-hour` are excluded by default. To add Spotlight Hours later, add `pokemon-spotlight-hour` to that list.

Events without a name, Leek Duck link, or valid start/end are skipped. Each calendar item has the event name, start/end, and Leek Duck link.

## Time handling

The feed has both timezone-naive local timestamps and UTC timestamps ending in `Z`. Naive timestamps are interpreted in `timezone` from `config.json` (`America/Chicago` by default); `Z` values are treated as UTC. The generated calendar stores absolute UTC instants, so calendar apps display the correct local time (including Central daylight-saving changes).

## Run locally

Requires Python 3.8 or newer. On Python 3.8 or Windows, install the timezone database dependency first:

```sh
python -m pip install -r requirements.txt
```

Then, to use the latest feed:

```sh
python generate_calendar.py
```

To generate from a downloaded JSON file instead:

```sh
EVENTS_JSON=events.json python generate_calendar.py
```

## Publish and subscribe

Put the code in your personal GitHub repository, enable GitHub Actions, then enable GitHub Pages from the `main` branch and `/docs` folder. The feed URL will be:

```text
https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/pokemon-go.ics
```

Subscribe to that URL from your calendar app rather than importing the file once; subscriptions can refresh when the workflow updates it. GitHub Pages and the repository must be public for a no-auth subscription.

The generator keeps event normalization separate from calendar rendering. A future detail-fetching/summary step can enrich each normalized event before it is written without changing the `.ics` output stage.

## Attribution

Event data is from [ScrapedDuck](https://github.com/bigfoott/ScrapedDuck) and Leek Duck. This is an unofficial community project.
