# Stock Metadata Embedder

Batch embed IPTC + XMP metadata from a CSV file into JPEG, PNG, EPS, and AI files.
Built for Adobe Stock contributors.

## Download

Go to the [Releases](../../releases) page and download `MetadataEmbedder.exe`.
Double-click to run — no installation needed. ExifTool is bundled inside.

## CSV Format

Your CSV needs at minimum a filename column. Supported fields:

| Column | Description |
|--------|-------------|
| filename | The image filename e.g. `photo1.jpg` |
| title | Image title / object name |
| keywords | Keywords separated by commas or semicolons |
| description | Caption / description |
| copyright | Copyright notice |

Column names are auto-detected but can be mapped manually inside the app.

## Supported Formats

- JPEG / JPG
- PNG
- EPS
- AI

## How It Works

1. Load your CSV file
2. Map your columns (auto-detected)
3. Select your image folder
4. Click **Embed Metadata Now**
5. Done — metadata is written directly into the files
