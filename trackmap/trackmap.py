from collections import namedtuple
import logging
from operator import itemgetter
import re
import string
import unicodedata

from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone

from spotify.spotify import spotify
from trackmap.models import Album, Track, TrackAvailability


AlbumInfo = namedtuple('AlbumInfo', 'id title year img_small img_medium img_large match_score')
ArtistInfo = namedtuple('ArtistInfo', 'id name multiple match_score')
TrackInfo = namedtuple('TrackInfo', 'id title match_score')
TrackArtistAlbum = namedtuple('TrackArtistAlbum', 'track_info artist_info album_info')


log = logging.getLogger(__name__)


def utc_now():
    return timezone.now().replace(tzinfo=timezone.utc)


def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nkfd_form if not unicodedata.combining(c)])


def chunks(l, n):
    """
    Breaks a single list into several lists of size n.
    :param list l: list to break into chunks
    :param int n: number of elements that each chunk should have
    :return: list of lists
    """
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]


class TrackSearch(object):

    # There are three cases a radioparadise artist name to be mapped to multiple spotify artist names:
    #       1. For example "Albert King & Stevie Ray Vaughan":  These are two artists playing together on one song
    #       2. For example 'Raymond Kane': ['Raymond Kane', 'Ray Kane']: This is one artist who has works attributed
    #          to them on Spotify under more than one name.
    #       3. Radio Paradise uses one name, Spotify uses another (e.g. 'Bob Marley': 'Bob Marley & The Wailers')
    #  These cases should be handled differently:
    #  For 1), the artist part of the query should include all the artists
    #  For 2), the artist names should be queried using OR.  If there are more than two mappings,
    #          this would mean making more than one query if the first query didn't find a good match.
    #  For 3), the Spotify version of the artist's name should be used in the query.
    MAPPING_TYPE_REPLACE = 'replace_single'
    MAPPING_TYPE_ONE_TO_MANY = 'one_to_many'
    MAPPING_TYPE_ANY_OF = 'any_of'
    REPLACE_FOR_SEARCH_ONLY = 'replace_single_search_only'

    rp_to_spotify_artist_map = {
        MAPPING_TYPE_REPLACE: {
            '!Deladap': '!Dela Dap',  # Spotify seems wrong on this one
            '10 CC': '10cc',
            'AfroCelts': 'Afro Celt Sound System',
            'Allman Brothers': 'The Allman Brothers Band',
            'Angélique Kidjo': 'Angelique Kidjo',
            'Bob Marley': 'Bob Marley & The Wailers',
            'Cheikh Lo Lo': 'Cheikh Lô',
            'Edie Brickell': 'Edie Brickell & New Bohemians',
            'English Beat': 'The Beat',
            'Ihtiyac Molasi': 'İhtiyaç Molası',
            'Iron & Wine and Calexico': 'Calexico / Iron and Wine',
            'Khachaturian': 'Aram Khachaturian',
            'Sixteen Horsepower': '16 Horsepower',
            'Sonny Boy Williamson': 'Sonny Boy Williamson II',
            'The English Beat': 'The Beat',
            'Trail of Dead': '...And You Will Know Us By The Trail Of Dead',
        },
        MAPPING_TYPE_ONE_TO_MANY: {
            'Albert King & Stevie Ray Vaughan': ['Albert King', 'Stevie Ray Vaughan'],
            'Ali Farka Touré & Ry Cooder': ['Ali Farka Touré', 'Ry Cooder'],
            'Ali Farka Touré & Toumani Diabeté': ['Ali Farka Touré', 'Toumani Diabeté'],
            'Alison Krauss & Gillian Welch': ['Alison Krauss', 'Gillian Welch'],
            'Anoushka Shankar & Karsh Kale': ['Anoushka Shankar', 'Karsh Kale'],
            'B.B. King & Dr. John': ['B.B. King', 'Dr. John'],
            'B.B. King & Mick Hucknall': ['B.B. King', 'Mick Hucknall'],
            'B.B. King & Tracy Chapman': ['B.B. King', 'Tracy Chapman'],
            'Ben Harper & the Blind Boys of Alabama': ['Ben Harper', 'The Blind Boys of Alabama'],
            'Beth Hart & Joe Bonamassa': ['Beth Hart', 'Joe Bonamassa'],
            'Beth Hart and Joe Bonamassa': ['Beth Hart', 'Joe Bonamassa'],
            'Billy Bragg & Wilco': ['Billy Bragg', 'Wilco'],
            'Blanquito Man, Control Machete & Celso Piña': ['Blanquito Man', 'Control Machete', 'Celso Piña'],
            'Bloomfield, Kooper, Stills': ['Al Kooper', 'Steve Stills'], # Spotify seems wrong to exclude Bloomfield.
            'Damon Albarn & Friends': ['Damon Albarn', 'Malian Musicians'],
            'Danger Mouse & Daniele Luppi': ['Danger Mouse', 'Daniele Luppi'],
            'Danger Mouse & Sparklehorse': ['Danger Mouse', 'Sparklehorse'],
            'Dave Matthews & Tim Reynolds': ['Dave Matthews', 'Tim Reynolds'],
            'David Byrne and Brian Eno': ['David Byrne', 'Brian Eno'],
            'David Tiller & Enion Pelta': ['David Tiller', 'Enion Pelta'],
            'Ella Fitzgerald & Joe Pass': ['Ella Fitzgerald', 'Joe Pass'],
            'Habib Koité & Bamada': ['Habib Koité', 'Bamada'],
            'J.J. Cale & Eric Clapton': ['J.J. Cale', 'Eric Clapton'],
            'Leftover Salmon & Cracker': ['Leftover Salmon', 'Cracker'],
            'Robert Plant & Alison Krauss': ['Robert Plant', 'Alison Krauss'],
            'Vishwa Mohan Bhatt & Jerry Douglas': ['Vishwa Mohan Bhatt', 'Jerry Douglas'],
        },
        MAPPING_TYPE_ANY_OF: {
            # These will be used when comparing the results returned from Spotify:
            'compare': {
                'Oliver Mtukudzi': ['Oliver Mtukudzi', 'Oliver Mtukudzi and The Black Spirits'],
                'Ryan Adams': ['Ryan Adams', 'Ryan Adams & The Cardinals'],
                'BÃ©la Fleck': ['Béla Fleck', 'Béla Fleck and the Flecktones'],
                'Béla Fleck': ['Béla Fleck', 'Béla Fleck and the Flecktones'],
                'Ben Harper': ['Ben Harper', 'Ben Harper And Relentless7'],
                'Josh Joplin Group': ['Josh Joplin', 'Josh Joplin Group'],
                'Elvis Costello': ['Elvis Costello', 'Elvis Costello & The Attractions', 'Elvis Costello And The Roots'],
                'Robyn Hitchcock': ['Robyn Hitchcock', 'Robyn Hitchcock & The Egyptians'],
                'Easy Star All-Stars': ['Toots & The Maytals', 'Citizen Cope', 'The Meditations'],  # see album: Radiodread
                'Raymond Kane': ['Raymond Kane', 'Ray Kane'],
                'Elephant Revival': ['Elephant Revival', 'Elephant Revivial'],
                '1 Giant Leap': ['Michael Stipe', 'Asha Bhosle'],
            },
            # These are used when searching Spotify; a separate search will be made for each separate name:
            'search': {
                # Note: no need to add alternates if the alternates also start with the same name, because
                #       Spotify will also match 'foo bar' if searching for an artist named 'foo'.
                'Easy Star All-Stars': ['Toots & The Maytals', 'Citizen Cope', 'The Meditations'],  # see album: Radiodread
                'Raymond Kane': ['Raymond Kane', 'Ray Kane'],
                'Elephant Revival': ['Elephant Revival', 'Elephant Revivial'],
                '1 Giant Leap': ['Michael Stipe', 'Asha Bhosle'],
            }
        },
        REPLACE_FOR_SEARCH_ONLY: {
            '10,000 Maniacs': 'Maniacs',  # Strange, but Spotify doesn't find it with 10000 Maniacs.
            'BÃ©la Fleck': 'Béla Fleck',
            'Josh Joplin Group': 'Josh Joplin',
        },
    }


    # Characters that can be stripped when comparing possible matches:
    strip_chars_pattern = re.compile('[{}]'.format(re.escape(string.punctuation + ' ')))

    # Characters that can be stripped when querying Spotify for a match:
    search_strip_chars_pattern = re.compile('[{}]'.format(
        re.escape(string.punctuation.replace('-', '').replace('&', '').replace('$', '').replace('#', ''))))

    # Match things like ", part 2":
    part_x_pattern = re.compile(',? (\((pt\.|part) \d+\)|(pt\.|part \d+))')

    # Match things like ", pt. 2", with a named group for the part number:
    part_x_type1 = re.compile(',? ?(pt\.|part) (?P<part_number>\d+)')

    # Match things like " (part 2)", with a named group for the part number:
    part_x_type2 = re.compile(' ?\((pt\.|part) (?P<part_number>\d+)\)')

    # Match things like "(w/ Markus Garvey)" and "feat. Jerry Garcia":
    featuring_pattern = re.compile('\((w/|feat\.?|featuring) (?P<featuring>[^\)]+)\)')

    contains_featuring_pattern = re.compile('^.*' + featuring_pattern.pattern + '.*$')

    # Match all non-alphanumeric characters (unicode aware):
    strip_non_words_pattern = re.compile('[\W_]+', re.UNICODE)

    # Match text like .*(live|acoustic)
    live_pattern = re.compile(r'^(.*?)(live|acoustic)$')

    # Match text like .*(\(live|acoustic\))
    live_raw_pattern = re.compile(r'^(.*?)\s*\(\s*(live|acoustic)\s*\)\s*$', re.IGNORECASE)

    # Match text like .*(live|acoustic)
    unplugged_pattern = re.compile(r'^(.*?)((mtvunplugged(version)?)|unpluggedversion)$')

    def __init__(self, query_limit=40, max_items_to_process=200):
        self.spotify = spotify()
        self.query_limit = query_limit
        self.max_items_to_process = max_items_to_process

    def spotify_query(self, song):
        and_artist_names_for_search, or_artist_names_for_search = self.map_artist_names(song.artists.all(), 'search')
        and_artist_names_for_compare, or_artist_names_for_compare = self.map_artist_names(song.artists.all(), 'compare')
        title = song.corrected_title or song.title

        # Query each possible or_artist_name separately, because an OR clause does not apply to only the artist names,
        # but instead seems to make all elements including the song, be considered as OR-ed elements.
        query_info = []
        for artist_name in or_artist_names_for_search:
            query = self.build_query(title, [artist_name])
            query_info.append((query, title, and_artist_names_for_compare, or_artist_names_for_compare))
        if and_artist_names_for_search:
            query = self.build_query(title, and_artist_names_for_search)
            query_info.append((query, title, and_artist_names_for_compare, or_artist_names_for_compare))

        return query_info

    def find_matching_tracks(self, song):
        """
        Gets the matching tracks that can be played per country.

        :param song: rphistory.Song object
        :return: tuple: (dict: best_matches, dict: matches_score)
        """

        #TODO: a fair number of the songs that fail to match fail because the song title is slightly different
        #      between radio paradise and spotify.  It might be worth a second pass that tries to find
        #      a song whose name almost matches on the album, if the album can be matched.

        best_matches = {}
        matches_score = {}
        for query, title, and_artist_names, or_artist_names in self.spotify_query(song):
            results = self.get_query_results(query)
            self.add_full_album_info(results)
            # TODO: check if any album_info matches were found.  If not, try to find album via asin.
            #       If asin album found and title not the same as original album title used in query,
            #       re-run query with asin album title and asin artists.
            #       # TODO: update rphistory album title and artists info?
            for item in results:
                # If the artist or track are not found, no need to process this item.
                track_info = self.extract_track_info(title, item)
                if track_info is None:
                    continue

                artist_info = self.extract_artist_info(song, and_artist_names, or_artist_names, item['artists'])
                if artist_info is None:
                    continue

                album_info = self.extract_album_info(song.album.title, song.album.release_year, item)

                # Find the best match per country.
                score = sum(info.match_score for info in [track_info, artist_info, album_info]) * 100
                for country in item['available_markets']:
                    previous_score = matches_score.get(country, -1)
                    if score > previous_score:
                        matches_score[country] = score
                        best_matches[country] = TrackArtistAlbum(
                            track_info=track_info, artist_info=artist_info, album_info=album_info
                        )

        return best_matches, matches_score

    def create_tracks(self, song, market_tracks, market_scores):
        """
        Create the tracks and artist objects, and collects the per-market TrackAvailability objects.

        :param song: rphistory.Song object
        :param market_tracks: map of country name string => TrackArtistAlbum namedtumple
        :param market_scores: map of country name string => match score
        :return: list of TrackAvailability objects
        """
        availabilities = []
        track_cache = {}
        for country, info in market_tracks.items():
            spotify_id = info.track_info.id
            track = track_cache.get(spotify_id, None)
            if not track:
                try:
                    track = self.get_or_create_track(info.track_info, info.artist_info, info.album_info)
                    track_cache[spotify_id] = track
                except IntegrityError as e:
                    log.warn("Problem (db integrity error)creating track for rp song {}: {}".format(song.rp_song_id, e))
                    continue
            track_availability = TrackAvailability(
                track=track, rp_song=song, country=country, score=market_scores[country])
            track_availability.full_clean(validate_unique=False)
            availabilities.append(track_availability)
        return availabilities

    @transaction.atomic
    def update_db_with_availibility(self, song, track_availabilities):
        """
        Atomically deletes previous track availability data and inserts new data

        :param song: rphistory.Song object
        :param track_availabilities: array of TrackAvailability objects
        :return:
        """
        TrackAvailability.objects.filter(rp_song=song).delete()
        if track_availabilities:
            TrackAvailability.objects.bulk_create(track_availabilities)

    def artist_query_fragment(self, artist_name):
        search_artist = self.rp_to_spotify_artist_map[self.REPLACE_FOR_SEARCH_ONLY].get(artist_name, artist_name)
        search_artist = self.prepare_text_for_search(search_artist)
        return 'artist:"{}"'.format(search_artist)

    def build_query(self, track_title, artist_names=None, album_title=None):
        """
        Builds a query based on the passed values.

        Note for or_artist_names: this only works when there are two artists, because the spotify API
        limits the query phrase to having one OR clause.

        :param track_title:
        :param artist_name: string or iterable of artist names
        :param album_title:
        :return: query string
        """
        search_track = self.strip_live_marker(track_title)
        search_track = self.prepare_text_for_search(search_track)
        q = ['track:"{}"'.format(search_track)]

        if artist_names:
            for name in artist_names:
                q.append(self.artist_query_fragment(name))

        if album_title:
            search_album = self.prepare_text_for_search(album_title)
            q.append('album:"{}"'.format(search_album))
        return ' '.join(q)

    def get_query_results(self, query, limit=None, max_items=None):
        """
        Gets as many query results as specified; handles Spotify's paging API.

        Note that max_items is not strict, all results from each page of results are added.
        E.g. with limit=5, max_items=7, you will get two full pages of results (10 items) if there are
        that many possible results.

        :param query: query dict like the one returned from build_query()
        :param limit: limit-per-page; defaults to self.query_limit
        :param max_items: max tracks to accumulate before returning.
        :return: array of track items
        """
        limit = limit or self.query_limit
        max_items = max_items or self.max_items_to_process
        all_items = []
        total = 0
        offset = 0
        keep_going = True
        while keep_going:
            results = self.spotify.search(q=query, type='track', limit=limit, offset=offset)
            items = results['tracks']['items']
            count = len(items)
            if count:
                all_items += items
                total += count
                offset += count
            keep_going = results['tracks']['next'] and total < max_items
            if total > max_items:
                log.warn("The query '{}' returned more than max_items={} results!".format(query, max_items))
        return all_items

    def add_full_album_info(self, items):
        """
        Adds full album info for the retrieved results, and adds a ``release_year`` element to the full album info.

        Modifies passed items.

        :param items: track query result items
        :return: None
        """
        # Spotify limits getting multiple albums in one query to 20 albums.
        max_ids = 20

        album_ids = {item['album']['id'] for item in items}
        id_lists = chunks(list(album_ids), max_ids)

        album_info = {}
        for id_list in id_lists:
            for album in self.spotify.albums(id_list)['albums']:
                album['release_year'] = album['release_date'].split('-')[0]
                album_info[album['id']] = album

        for item in items:
            item['album'] = album_info[item['album']['id']]

    def match_artist(self, artist, artist_list):
        artist_simple = self.simplified_text(artist)
        for a in artist_list:
            a_simple = self.simplified_text(a['name'])
            if a_simple == artist_simple:
                return 1.0, a

            a_alternate = 'the' + a_simple
            artist_alternate = 'the' + artist_simple
            if a_alternate == artist_alternate:
                return 0.9, a

            if len({artist_simple, artist_alternate, a_simple, a_alternate}) < 4:
                # One of expected and existing pairs matched
                return 0.8, a
        return 0.0, None

    def extract_artist_info(self, song, artist_names, alternative_artist_names, artist_list):
        """
        Find a matching artist. There may be many artists, if there are then the match_score is proportionally
        higher according to the number of matched artist names.

        Spotify's search api doesn't allow for requiring exact matches, so we try here to do a reasonably
        good job of detecting a matching artist name.

        :param Song song:
        :param artist_names: array of artist names provided by source
        :param artist_names: array of artist names, one of which should match, provided by source
        :param artist_list: array of spotify API album artist results
        :return: ArtistInfo
        """

        match_score = 0
        highest_artist_match_score = 0
        best_artist_match = None

        for artist in artist_names:
            score, matched_artist = self.match_artist(artist, artist_list)
            if score > 0:
                match_score += score
                if highest_artist_match_score < score:
                    best_artist_match = matched_artist

        for artist in alternative_artist_names:
            score, matched_artist = self.match_artist(artist, artist_list)
            if score > 0:
                match_score += score
                if highest_artist_match_score < score:
                    best_artist_match = matched_artist
                break

        if match_score > 0:
            # Ideally, all artist names should match.  If alternative artist names are provided,
            # then one of them should match.
            max_matches = len(artist_names) + int(len(alternative_artist_names) > 0)
            artist_count = len(artist_list)
            multiple =  artist_count > 1
            score = match_score / max_matches
            return ArtistInfo(
                id=best_artist_match['id'], name=best_artist_match['name'], multiple=multiple, match_score=score)
        else:
            message = "Artists '{}' not found in list: {}".format(
                    artist_names + alternative_artist_names, [a['name'] for a in artist_list]
            )
            log.debug(message)
            return None

    def extract_album_info(self, expected_album, expected_year, item):
        album = item['album']
        expected_simple = self.simplified_text(expected_album)
        item_simple = self.simplified_text(album['name'])
        item_year = int(album['release_year'])
        match_score = int(item_simple == expected_simple)
        if match_score:
            # Only add points for year match if album title matched.
            match_score += int(expected_year == item_year)
        img_small = None
        img_med = None
        img_large = None
        images = sorted(album['images'], key=itemgetter('height'))
        count = len(images)
        if count == 1:
            img_small = img_med = img_large = images[0]['url']
        elif count == 2:
            img_small = images[0]['url']
            img_med = img_large = images[1]['url']
        elif count > 2:
            img_small = images[0]['url']
            img_med = images[-2]['url']
            img_large = images[-1]['url']
        return AlbumInfo(
            id=album['id'], title=album['name'], year=item_year,
            img_small=img_small, img_medium=img_med, img_large=img_large,
            match_score=match_score
        )

    def extract_track_info(self, track_title, item):
        track_simple = self.simplified_text(track_title)
        item_track_simple = self.simplified_text(item['name'])

        match_score = self.track_info_match(track_title, track_simple, item_track_simple)

        if not match_score and self.contains_featuring_pattern.match(track_title):
            # Retry without the "featuring" text
            track_simple = self.simplified_text(track_title, leave_feature=False)
            match_score = self.track_info_match(track_title, track_simple, item_track_simple)
            if match_score:
                match_score -= 0.1

        if not match_score:
            stripped = self.strip_live_marker(track_title)
            if stripped != track_title:
                # Retry without the "live" text
                track_simple = self.simplified_text(stripped, leave_feature=False)
                match_score = self.track_info_match(track_title, track_simple, item_track_simple)
                if match_score:
                    match_score -= 0.2

        if match_score > 0:
            return TrackInfo(id=item['id'], title=item['name'], match_score=match_score)
        else:
            message = "Expected track: {}, found track: {}".format(track_title, item['name'])
            log.debug(message)
        return None

    def track_info_match(self, expected_title, expected_title_simple, search_result_title_simple):
        match_score = 1.0
        track_match = expected_title_simple == search_result_title_simple

        if not track_match:
            # Accept things like "the <song name> 2004 remaster":
            match_score = 0.9
            regex = r"^(the)?" + expected_title_simple + r"(\d{4})?((digital)?(remaster(ed)?)(version)?)?"
            track_match = re.match(regex, search_result_title_simple)

            if not track_match:
                # Accept things like "the <song name> - instrumental ":
                match_score = 0.6
                regex = r"^(the)?" + expected_title_simple + r"(instrumental|vocal|acoustic|live|original)?"
                track_match = re.match(regex, search_result_title_simple)

                if not track_match:
                    # Sometimes there are songs like "Song (live)" that should match "Song [MTV Unplugged Version]"
                    match_score = 0.5
                    if '(' in expected_title:
                        try:
                            base_track = self.live_pattern.match(expected_title_simple).groups()[0]
                            base_item = self.unplugged_pattern.match(search_result_title_simple).groups()[0]
                            track_match = base_track == base_item
                        except:
                            # One of regexes failed to match ... give up.
                            pass

                    if not track_match:
                        match_score = 0

        return match_score

    @transaction.atomic
    def get_or_create_track(self, track_info, artist_info, album_info):
        """
        Gets or creates the track, also getting or creating the album.

        :param TrackInfo track_info:
        :param ArtistInfo artist_info:
        :param AlbumInfo album_info:
        :return: Track
        """
        album_defaults = {
            'title': album_info.title,
            'img_small_url': album_info.img_small,
            'img_medium_url': album_info.img_medium,
            'img_large_url': album_info.img_large,
            }
        album_obj = self.get_or_create_and_update_if_needed(Album, {'spotify_id': album_info.id}, album_defaults)

        track_defaults = {
            'title': track_info.title,
            'album': album_obj,
            'artist': artist_info.name,
            'artist_id': artist_info.id,
            'many_artists': artist_info.multiple,
            }
        track_obj = self.get_or_create_and_update_if_needed(Track, {'spotify_id': track_info.id}, track_defaults)
        return track_obj

    def get_or_create_and_update_if_needed(self, model, kwargs, defaults):
        """
        Similar to Django's get_or_create / update_or_create, but only updates if something changed.

        :param model: model class
        :param kwargs: dict of field/value pairs used to identify an existing object
        :param defaults: dict of field/value paris that will be used for other, non-identifying fields
        :return:
        """
        # TODO: should clean before creating, too.
        obj, created = model.objects.get_or_create(defaults=defaults, **kwargs)

        # Save back to DB if any info has changed.
        if not created:
            clean_exclude = list(kwargs)
            changed = False
            for k, v in defaults.items():
                if getattr(obj, k) != v:
                    changed = True
                    setattr(obj, k, v)
                else:
                    clean_exclude.append(k)
            if changed:
                obj.full_clean(exclude=clean_exclude, validate_unique=False)
        return obj

    # TODO: should these be managed in the DB?
    def map_artist_names(self, artists, for_action):
        """
        Replace Radio Paradise name with Spotify name for some artists that are named differently by the two services.

        :param artists: iterable of Artist objects
        :param str for_action: 'search' or 'compare'
        :return: tuple: (and_artists, or_artists)
        """
        if for_action not in ['compare', 'search']:
            raise ValueError("for_action parameter must be 'compare' or 'search'")

        and_artists = []
        or_artists = []
        for artist in artists:
            mapped = self.rp_to_spotify_artist_map[self.MAPPING_TYPE_REPLACE].get(artist.name)
            if mapped is not None:
                and_artists.append(mapped)
                continue

            mapped = self.rp_to_spotify_artist_map[self.MAPPING_TYPE_ONE_TO_MANY].get(artist.name)
            if mapped is not None:
                and_artists += mapped
                continue

            mapped = self.rp_to_spotify_artist_map[self.MAPPING_TYPE_ANY_OF][for_action].get(artist.name)
            if mapped is not None:
                or_artists += mapped
                continue

            and_artists.append(artist.name)

        return and_artists, or_artists

    def simplified_text(self, string, leave_feature=True):
        string = string.lower().replace(' & ', ' and ').replace(' + ', ' and ')
        string = re.sub(self.part_x_type1, ' part\g<part_number>', string)
        string = re.sub(self.part_x_type2, ' part\g<part_number>', string)
        string = self.remove_featuring(string, leave_feature=leave_feature)
        string = self.remove_leading_article(string)
        string = remove_accents(self.strip_non_words_pattern.sub('', string))
        return re.sub(self.strip_chars_pattern, '', string)

    def prepare_text_for_search(self, text):
        """
        Remove accents and remove leading 'a ' or 'the ', and punctuation characters.
        """
        if text is None:
            return None

        plain_text = remove_accents(text).strip().lower()
        plain_text = self.remove_leading_article(plain_text)
        plain_text = self.remove_part_x(plain_text)
        plain_text = self.remove_featuring(plain_text, leave_feature=False)
        plain_text = self.search_strip_chars_pattern.sub('', plain_text)
        return plain_text.strip()

    def remove_leading_article(self, text):
        """
        Remove a leading 'a ' or 'the ', but only if the remaining string is at least 3 characters long.

        :param str text:
        :return: str
        """
        if text.startswith('a '):
            stripped_text = text[2:]
        elif text.startswith('the '):
            stripped_text = text[4:]
        else:
            return text

        if len(stripped_text) < 3:
            return text

        return stripped_text

    def remove_part_x(self, text):
        return re.sub(self.part_x_pattern, '', text)

    def remove_featuring(self, text, leave_feature):
        """
        Transform things like "(w/ foo)" or "(featuring foo)" to simply "featuring foo" (or remove it completely)

        :param text:
        :param leave_feature: if True, do not remove "foo" if (w/ foo) is matched.  if False, remove the entire match.
        :return:
        """

        if leave_feature:
            return re.sub(self.featuring_pattern, 'featuring \g<featuring>', text)
        else:
            return re.sub(self.featuring_pattern, '', text)

    def strip_live_marker(self, track_title):
        match = self.live_raw_pattern.match(track_title)
        if match:
            return match.groups()[0]
        else:
            return track_title
