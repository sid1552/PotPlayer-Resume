# PotPlayer Resume

A modern GUI application that automatically tracks and resumes playback positions for network streams in PotPlayer

## Why This App?

### The Problem

Most media players don't aggressively cache network streams, leading to buffering and stuttering. Only a few players like **MPV** and **PotPlayer** provide robust stream caching.

However, **PotPlayer is the ONLY player** that combines all three of these features:

- **RTX Video Enhancement** (AI-powered upscaling and HDR)
- **RTX VSR** (Video Super Resolution)
- **Aggressive stream caching** for smooth playback
- **BUT** no native support for resuming network streams

**No other player offers all three capabilities together!**

### The Solution

This app bridges that gap by adding **smart resume functionality** to PotPlayer, giving you:

- The best streaming performance with RTX enhancements
- Automatic position tracking for network URLs
- Seamless resume across different streaming sessions

**TL;DR**: Get PotPlayer's unique combination of RTX features + aggressive caching + the convenience of automatic resume that it's missing!

## Features

- **Smart Resume**: Automatically saves and resumes playback positions for network URLs
- **Modern Dark UI**: Beautiful, clean interface with dark theme
- **Media Library**: Track multiple videos with metadata (quality, source, file size)
- **Smart Parsing**: Automatically extracts movie names, quality, and source information
- **Network Streams**: Works with HTTP/HTTPS streaming URLs
- **Position History**: Keep track of all your watched content with timestamps
- **One-Click Resume**: Double-click any saved position to continue watching
- **Clipboard Integration**: Paste and play URLs directly from clipboard

## Screenshots
<img width="1203" height="740" alt="{9D23BC4E-42D2-4EEA-97C9-A0C7519377B8}" src="https://github.com/user-attachments/assets/47bb2586-1359-4d81-a6e0-bb264b28d0cc" />


### Main Interface
The application features a clean, modern interface with:
- URL input with play controls
- Real-time playback monitoring with progress bar
- Organized table view of all saved positions
- Movie metadata including quality, source, and file size

## Getting Started

### Prerequisites

- **Windows OS** (7, 8, 10, or 11)
- **Python 3.7+**
- **PotPlayer** (Download from [official site](https://potplayer.daum.net/))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sid1552/PotPlayer-Resume.git
   cd potplayer-resume
   ```

2. **Run the application**
   ```bash
   python potplayer_resume_clean.py
   ```

   No external dependencies required! Uses only Python standard library.

### Quick Start

1. **Launch the app**
   ```bash
   python potplayer_resume_clean.py
   ```

2. **Enter a streaming URL** or click "Paste & Play" to use clipboard content

3. **The app will**:
   - Check if you've watched this video before
   - Resume from your last position if available
   - Monitor playback and save your progress automatically

4. **When you close PotPlayer**, your position is automatically saved!

## Usage

### Playing a Video

**Method 1: Manual Entry**
1. Paste or type the streaming URL in the input field
2. Click "Play" or press Enter

**Method 2: Quick Paste**
1. Copy a streaming URL to your clipboard
2. Click "Paste & Play"

### Managing Saved Positions

- **Resume**: Double-click any entry in the table
- **Copy URL**: Right-click → Copy URL
- **Delete**: Right-click → Delete
- **Clear All**: Click "Clear All" button

### Settings

Click the "Settings" button to:
- Configure custom PotPlayer installation path
- Auto-detect PotPlayer location
- Verify installation

## Features in Detail

### Smart Movie Name Parsing

The app intelligently extracts clean movie names from filenames:

```
Movie.Name.2024.1080p.BluRay.x264.mkv → Movie Name
A.Farewell.1908.2160p.WEB-DL.HDR.mkv → A Farewell
```

### Metadata Extraction

Automatically detects:
- **Quality**: 4K, 1080p, 720p, 480p, etc.
- **Source**: BluRay, WEB-DL, WEBRip, HDTV, etc.
- **File Size**: Fetched from network headers
- **Last Watched**: Timestamp of last playback

### Real-time Monitoring

While PotPlayer is running:
- Live position display (HH:MM:SS)
- Progress bar showing playback percentage
- Duration tracking
- Automatic position saving every 2 seconds

## File Structure

```
potplayer-resume/
│
├── potplayer_resume_clean.py    # Main application
├── README.md                     # This file
│
└── Data Files (auto-created in user home):
    ├── .potplayer_positions.json       # Saved positions
    └── .potplayer_resume_settings.json # App settings
```

## Configuration

### Default PotPlayer Paths

The app searches these locations automatically:
```
C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe
C:\Program Files\PotPlayer\PotPlayerMini64.exe
C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe
```

### Data Storage

Positions are stored in JSON format at:
```
%USERPROFILE%\.potplayer_positions.json
```

Example entry:
```json
{
  "A Farewell": {
    "timestamp": "01:23:45",
    "seconds": 5025,
    "updated": "2024-02-14 15:30:00",
    "current_url": "https://example.com/movie.mkv",
    "file_size": "2.1GB"
  }
}
```

## Technical Details

### How It Works

1. **Launch Detection**: Monitors PotPlayer window using Win32 API
2. **Position Tracking**: Polls playback position via Windows messages (WM_USER)
3. **Smart Saving**: Only saves positions after 5+ seconds of playback
4. **Resume Logic**: Passes `/seek=HH:MM:SS` parameter to PotPlayer

### Win32 API Integration

```python
# Window detection
FindWindow("PotPlayer64", None)

# Position query
SendMessage(hwnd, WM_USER, 0x5004, 0)  # Get position
SendMessage(hwnd, WM_USER, 0x5002, 0)  # Get duration
```

## Theming

The app uses a custom dark theme inspired by Catppuccin:

| Element | Color |
|---------|-------|
| Background | `#1e1e2e` |
| Accent | `#89b4fa` |
| Success | `#a6e3a1` |
| Warning | `#f9e2af` |
| Error | `#f38ba8` |

## Troubleshooting

### PotPlayer Not Found

**Problem**: App shows "PotPlayer: Not Found"

**Solution**:
1. Click "Settings"
2. Click "Auto-Detect PotPlayer"
3. Or manually browse to PotPlayer executable

### Position Not Resuming

**Problem**: Video starts from beginning despite saved position

**Solution**:
- Ensure you're using the same URL
- Movie name matching is used - different URLs for the same movie will resume correctly
- Check if position was saved (should appear in table)

### Monitoring Not Working

**Problem**: Position not updating while playing

**Solution**:
- Ensure PotPlayer is actually playing (not paused)
- Position only updates after 5 seconds of playback
- Check if PotPlayer window is detected (check status bar)

## License

This project is licensed under the MIT License - see below for details:

```
MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Ideas for Contributions

- Tray icon with notifications
- Trakt.tv integration - Sync watch progress and scrobble to Trakt
- Stremio Desktop integration - Direct launch from Stremio with position tracking
- Export/import position database

## Acknowledgments

- **PotPlayer** by Daum for the excellent media player
- **Catppuccin** color scheme for design inspiration
- Python's built-in `tkinter` for the GUI framework

## Contact

If you have questions or suggestions:
- Open an [Issue](https://github.com/sid1552/PotPlayer-Resume/issues)

---

Made with care for PotPlayer users. If you find this useful, please star the repository!
