# QGisFileSync #

QGis-Python-Plugin to scan directories and create/update/synchronize layers with extracted file metadata


Original purpose:
Digital photos with GPS-lat/lon coordinates in Exif-header.

## Three modes for usage: ##

### PreScan ###
- Quick scan a directory and create temporary point-layer with the extracted meta-data
- GPS-meta-data in jpegs will be used for feature-geometry (PointZ)

### Sync ###
- the PreScan-result-layer can be synced with any other point-layer, e.g. to successively build up a georeferenced digital photo archive

### PostScan ###
- refresh or complete extracted file-metas in existing layer

## Addendum ##
- The plugin has been developed under the latest versions since 2025, currently
  - 3.42.3-Münster
  - 3.34.10-Prizren (LTR)
  - Windows (10 + 11)
  - Linux (Ubuntu/Mint 21.2)
- not tested (but should run) with older QGis-3-Versions
- not tested on macOS
- please report bugs or ideas for missing features 
- or translation-errors :-)



## More Instructions: ##
[docs/index.en.html](https://htmlpreview.github.io/?https://github.com/Ludwig-K/QGisLinearReference/blob/main/docs/index.en.html)


## Contribute ##
- Issue Tracker: https://github.com/Ludwig-K/QGisLinearReference/issues
- Source Code: https://github.com/Ludwig-K/QGisLinearReference

## Support ##
If you are having issues, please let me know.
You can directly contact me via ludwig[at]kni-online.de

## License ##
The project is licensed under the GNU GPL 3 license.
