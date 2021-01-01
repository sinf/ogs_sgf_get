
# online-go.com SGF downloader script

```
usage: sgf_get.py [-h] [-l LIMIT] [-o OUTPUTDIR] [-k] USERNAME [USERNAME ...]

Fetches at most LIMIT most recent games (most recent first) of user USERNAME
from online-go.com. SGF files are saved to directory OUTPUTDIR. You can re-run
this script whenever to keep your local SGF collection up to date.

positional arguments:
  USERNAME              Can specify multiple usernames. Case sensitive

optional arguments:
  -h, --help            show this help message and exit
  -l LIMIT, --limit LIMIT
                        Maximum number of recent games to check. Default 100.
                        Use -1 for no limit.
  -o OUTPUTDIR, --outputdir OUTPUTDIR
                        Default ./sgf
  -k, --keep-going      Keep going all the way into the past even if many
                        games are found to be already downloaded
```

