from lxml import etree as ET
from dataclasses import dataclass, fields
from typing import Any
from pathlib import Path
import inspect


@dataclass(repr=True)
class Track:
    # Define properties useful for this project
    track_id: int
    name: str
    artist: str = ""
    album: str = ""
    rating: int = 0
    track_number: int | None = None
    year: int | None = None

    @classmethod
    def from_xml(cls, track_xml: ET.Element) -> "Track":
        d = {}
        for key in track_xml.iter():
            if key.tag == "key":
                value = next(key.itersiblings())
                # Enforce snake case for keys
                d[snake_case(key.text)] = value.text

        if "rating" in d:
            # Correct rating from XML % to star rating
            d["rating"] = star_rating(d["rating"])

        # Remove parameters not useful for this project
        d = {k: v for k, v in d.items() if k in inspect.signature(cls).parameters}

        return cls(**d)

    def __str__(self):
        return (
            f"Track: {self.name} by {self.artist}, "
            f"Album: {self.album}, "
            f"Rating: {self.rating}"
        )


class Library:
    def __init__(self, tracks: list[Track]) -> None:
        self.tracks = tracks

    @classmethod
    def from_xml(cls, library_xml_path: str | Path) -> "Library":
        tree = ET.parse(library_xml_path)
        root = tree.getroot()
        tracks_root = root.xpath("//dict/dict/dict")
        return cls(tracks=[Track.from_xml(track_xml) for track_xml in tracks_root])

    def to_albums(self) -> list["Album"]:
        album_name_tracks_dict = {}
        for t in self.tracks:
            if t.album not in album_name_tracks_dict:
                album_name_tracks_dict[t.album] = []

            album_name_tracks_dict[t.album].append(t)

        return [Album(tracks) for tracks in album_name_tracks_dict.values()]

    def __repr__(self):
        return f"{self.__class__.__name__}(tracks={self.tracks[:10]}...)"

    def __str__(self):
        return f"{self.__class__.__name__} with {len(self.tracks)} tracks"

    def __iter__(self):
        return iter(self.tracks)

    def __getitem__(self, index):
        return self.tracks[index]


class Album(Library):
    def __init__(self, tracks: list[Track]) -> None:
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
        non_zero_ratings = [r for r in self._ratings if r is not None and r > 0]
        return len(non_zero_ratings) / len(self.tracks)


def snake_case(title_case_str: str) -> str:
    return title_case_str.lower().replace(" ", "_")


def star_rating(rating: int) -> int:
    return int(rating) // 20 if rating is not None else 0


def print_element(e: ET.ElementBase) -> None:
    print(ET.tostring(e, pretty_print=True))


# Replace 'your_itunes_library.xml' with the actual path to your iTunes Library XML file
LIBRARY_XML_PATH = Path(
    "/Users/stephen/Music/Apple Music/20240226 iTunes Music Library.xml"
)

if __name__ == "__main__":
    library = Library.from_xml(LIBRARY_XML_PATH)
    albums = library.to_albums()

    for album in albums:
        if album.percent_rated > 0.5 and album.max_rating <= 3:
            print(
                f"{','.join(album.artists)} - {album.name} "
                f"- {album.percent_rated:.0%} rated "
                f"- max {album.max_rating} - avg {album.avg_rating:.2f}"
            )
