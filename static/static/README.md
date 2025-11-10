# Static Assets Directory

This directory contains static assets for the B2B Insights application.

## Directory Structure

```
static/
├── css/
│   └── landing.css          # Landing page styles
├── images/
│   └── q-icon.svg           # Q character icon (REPLACE WITH ACTUAL ICON)
└── fonts/
    └── (Place Rale Grotesk font files here)
```

## Required Fonts

You need to add the **Rale Grotesk Base** font family files in the `fonts/` directory:

- `RaleGrotesk-Regular.woff2` (Regular weight, normal style)
- `RaleGrotesk-RegularItalic.woff2` (Regular weight, italic style)
- `RaleGrotesk-Thin.woff2` (Thin weight, normal style)
- `RaleGrotesk-ThinItalic.woff2` (Thin weight, italic style)
- `RaleGrotesk-Medium.woff2` (Medium weight - 500)
- `RaleGrotesk-Black.woff2` (Black weight - 900)
- `RaleGrotesk-BlackItalic.woff2` (Black weight - 900, italic style)

The font declarations are already set up in `css/landing.css`.

## Q Icon

Replace `images/q-icon.svg` with your actual Q character icon. The current file is just a placeholder.

## Usage

The static files are served via Flask at the `/static/` route. For example:
- CSS: `/static/css/landing.css`
- Q Icon: `/static/images/q-icon.svg`
- Fonts: `/static/fonts/RaleGrotesk-Regular.woff2`

