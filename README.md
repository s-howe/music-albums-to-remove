# music albums to remove

A useful script to modify or extend in order to tidy up an iTunes/Apple Music library.

The script parses the iTunes/Apple Music library.xml file to provide an interface for
finding albums with low ratings or low play counts.

## Current usage

I am currently using the script to identify albums that contain tracks with ratings, 
but have a low average rating across the album. I want to delete these albums to tidy up
my Apple Music library.

``` bash
python albums_to_remove.py "/path/to/my/library.xml" > albums_to_remove.txt
```
