# Keeping the profile current

The introduction and story in `README.md` are edited by hand. The first three
selected highlights on <https://www.jacquesblom.com/> are copied into the section
between `WEBSITE HIGHLIGHTS START` and `WEBSITE HIGHLIGHTS END`.

This follows the homepage's editorial order, not commit activity or a claim that
archived tutorials are new. Titles, links, descriptions, and original date/type
labels come from the live site. Update the homepage's selections when publishing
work you want featured on GitHub. The site's RSS currently contains library
entries only, so it would omit projects such as Counted.

The GitHub Action checks on Mondays at 08:23 Cape Town time, on relevant changes
to `master`, and when run manually from Actions → Sync website highlights.
Only changes to the generated section produce a commit. It uses the repository's
`GITHUB_TOKEN`; no personal access token, API key, or paid service is needed.
Pull requests run tests and a live extraction without pushing changes.

The parser reads the published HTML section labelled `library-heading`. If the
website changes that markup, returns an error, or has missing highlight fields,
the job fails before writing the README. Check the Actions failure notification
and update the parser if needed. Existing highlights remain available.

GitHub [disables schedules after 60 days without repository activity](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
If the profile has been quiet, re-enable the workflow in Actions and run it
manually. A website change alone does not reactivate a disabled GitHub schedule.
The workflow must be merged to `master` before scheduled updates can begin.

## Local verification

Python 3.10+ is sufficient; there are no third-party dependencies.

```sh
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/sync_website.py
git diff -- README.md
```

For an offline check, pass `--html /path/to/saved-homepage.html`. To preview in
another file, pass `--readme /path/to/README.md`.

## Previous YouTube updater

The previous README used `jacques-blom/dynamic-github-profile`, a Netlify function
called by a YouTube webhook. Its source does not check for missing markers before
writing. The new README removes that old video section, but cannot disable an
external deployment. If the old function or webhook is still deployed, retire it
so a future YouTube upload cannot append the old video list to this profile.
