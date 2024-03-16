from lxml import etree as ET
from dataclasses import dataclass
from pathlib import Path
import inspect
from argparse import ArgumentParser


def parse_args():
    parser = ArgumentParser(
        description="Recommend albums to remove from iTunes/Apple Music by parsing "
        "the library XML file."
    )
    parser.add_argument(
        "library_xml_file_path",
        type=Path,
        help=(
            "Path to the iTunes/Apple Music library XML file. This is usually found "
            " at /Users/username/Music/Music/library.xml"
        ),
    )
    return parser.parse_args()


# Some util functions
def snake_case(title_case_str: str) -> str:
    return title_case_str.lower().replace(" ", "_")


def star_rating(percent_rating: int | None) -> int:
    """Track ratings are stored as percents in increments of 20 in iTunes/Apple Music XML
    format e.g. 1* = 20%, 5% = 100%. Convert the XML percent rating to the integer star
    rating."""
    return int(percent_rating) // 20 if percent_rating is not None else 0


@dataclass(repr=True)
class Track:
    """A music track."""

    # Define only the properties useful for this project
    track_id: int
    name: str
    artist: str = ""
    album: str = ""
    rating: int = 0
    track_number: int | None = None
    year: int | None = None
    file_size: int = 0  # size in bytes
    time: int | None = 0  # time in ms

    @classmethod
    def from_xml(cls, track_xml: ET.Element) -> "Track":
        """Build a Track by parsing the XML of a track node in the format given in an
        iTunes/Apple Music Library.xml file."""
        # Build a dict of all key-value pairs in the XML
        d = {}
        for key in track_xml.iter():
            if key.tag == "key":
                value = next(key.itersiblings())
                # Enforce snake case for keys
                d[snake_case(key.text)] = value.text

        if "rating" in d:
            # Correct rating from XML % rating to star rating
            d["rating"] = star_rating(d["rating"])

        # Correct keys for time and file_size
        if "total_time" in d:
            d["time"] = d.pop("total_time")

        if "size" in d:
            d["file_size"] = int(d.pop("size"))

        # Remove parameters not useful for this project
        dataclass_params = inspect.signature(cls).parameters
        d = {k: v for k, v in d.items() if k in dataclass_params}

        return cls(**d)

    def __str__(self):
        return (
            f"Track: {self.name} by {self.artist}, "
            f"Album: {self.album}, "
            f"Rating: {self.rating}"
        )


class Library:
    """Representation of an iTunes/Apple Music Library as a simple collection of tracks.

    Library acts as an iterator of tracks, e.g.
        - `for track in library:`
        - `for track in library[:5]:`
    """

    def __init__(self, tracks: list[Track]) -> None:
        self.tracks = tracks

    @classmethod
    def from_xml(cls, library_xml_path: str | Path) -> "Library":
        """Build a track by parsing the XML tree for a library as is given in an
        iTunes/Apple Music Library.xml file"""
        tree = ET.parse(library_xml_path)
        root = tree.getroot()
        tracks_root = root.xpath("//dict/dict/dict")
        return cls(tracks=[Track.from_xml(track_xml) for track_xml in tracks_root])

    def to_albums(self) -> list["Album"]:
        """Group tracks into albums. Albums are currently simply grouped by name and
        year, so be aware that if multiple artists have the same album name and year, a
        single Album object would be produced containing all those tracks."""

        # Create a dict of {(album_name, album_year): [track1, track2]}
        album_tracks_dict = {}
        for t in self.tracks:
            album_key = (t.album, t.year)
            if album_key not in album_tracks_dict:
                album_tracks_dict[album_key] = []

            album_tracks_dict[album_key].append(t)

        # Create album objects from each list of tracks
        return [Album(tracks) for tracks in album_tracks_dict.values()]

    @property
    def size(self):
        return len(self.tracks)

    @property
    def file_size(self):
        return sum(t.file_size for t in self.tracks)

    @property
    def total_time(self):
        return sum(t.time for t in self.tracks)

    def __repr__(self):
        return f"Library(tracks={self.tracks[:10]}...)"

    def __str__(self):
        return f"Library with {len(self.tracks)} tracks"

    def __iter__(self):
        return iter(self.tracks)

    def __getitem__(self, index):
        return self.tracks[index]


class Album(Library):
    """Representation of an album as a simple collection of tracks."""

    def __init__(self, tracks: list[Track]) -> None:
        if not all(track.album == tracks[0].album for track in tracks):
            raise ValueError(
                "Cannot create an album from tracks that do not share the same album property."
            )

        self.tracks = tracks

        self.name = self.tracks[0].album
        self.artists = sorted(list(set(t.artist for t in tracks)))

        self._ratings = [t.rating for t in tracks]

    def __str__(self):
        return (
            f"Album: {self.name} by {','.join(self.artists)} "
            f"with {len(self.tracks)} tracks"
        )

    @property
    def min_rating(self) -> int:
        return min(self._ratings)

    @property
    def max_rating(self) -> int:
        return max(self._ratings)

    @property
    def avg_rating(self) -> float:
        return sum(self._ratings) / len(self._ratings)

    @property
    def percent_rated(self) -> float:
        """The percent of tracks in the album that have non-zero ratings."""
        non_zero_ratings = [r for r in self._ratings if r is not None and r > 0]
        return len(non_zero_ratings) / len(self.tracks)


if __name__ == "__main__":
    args = parse_args()

    if not Path(args.library_xml_file_path).exists():
        raise FileNotFoundError(
            f"Given library XML file path does not exist: {args.library_xml_file_path}"
        )

    library = Library.from_xml(args.library_xml_file_path)
    albums = library.to_albums()

    albums_sorted = sorted(albums, key=lambda a: a.file_size, reverse=True)

    for album in albums_sorted:
        if album.percent_rated > 0.01 and album.max_rating <= 3:
            print(
                f"{','.join(album.artists)} - {album.name} "
                f"- tracks: {len(album.tracks)} "
                f"- size: {album.file_size / (1024**2):.0f}MB "
                f"- {album.percent_rated:.0%} rated "
                f"- max {album.max_rating} - avg {album.avg_rating:.2f}"
            )
