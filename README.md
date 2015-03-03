# rpspot

A Django project which allows generating Spotify playlists which match, as far as possible,
the songs that were played on [Radio Paradise](http://www.radioparadise.com/)

It does this by recording the playlist history of Radio Paradise, and mapping those songs
to available Spotify songs in different countries.  This is obviously not 100% possible,
because not all the songs that air on Radio Paradise are available in all (or even any)
Spotify markets.  As of February 2015, it manages to find about 88% of the songs that
aired on Radio Paradise.

Sounds interesting, but you don't want to install this, you just want to use it?
You can use it here: (todo: insert url).

You want to install it yourself and customize it?  Great, go ahead.  The license is
a two-clause BSD license.  If you make it better, pull requests are welcome!

## Installation requirements
Beyond the python packages listed in requirements.txt, there are some other dependencies:

* A database (the project was developed and tested using Postgresql 9.4, other databases should work too).
* A Spotify Developer [account](https://devaccount.spotify.com/my-account/)
* GeoIP must be [installed](https://docs.djangoproject.com/en/1.8/ref/contrib/gis/geoip/)
* The GeoLite Country .dat file needs to be available at the path specified by the setting ``GEOIP_PATH``

## Configuration for different environments
Copy the ``env-dist`` file to ``.env`` and edit the settings as appropriate.

## Loading playlist and mapping tracks
To fetch the playlist from Radio Paradise:
```
./manage.py load_playlist --playlist now_4.xml
```

To map the fetched Radio Paradise songs to available Spotify songs:
```
./manage.py map_tracks
```

See also cron-* in the examples folder for example scripts to call from cron.

## Frontend development
See the README in the foundation-framework folder.
