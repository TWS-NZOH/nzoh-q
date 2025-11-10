# Landing Page Setup Guide

## Overview

The new landing page features a conversational, step-by-step interface with Q (the AI assistant) guiding users through report generation.

## What's Been Created

### 1. New Multi-Step Landing Experience
- **Step 1**: Q introduces itself and asks for user's initials
- **Step 2**: Shows accounts owned by that user (from Salesforce)
- **Step 3**: Animated loading state while generating report  
- **Step 4**: Completion message with "back" button option

### 2. Files Created/Modified

**New Files:**
- `static/css/landing.css` - All styling for the landing page
- `static/images/q-icon.svg` - Placeholder Q icon (REPLACE THIS!)
- `static/README.md` - Instructions for static assets
- `LANDING_PAGE_SETUP.md` - This file

**Modified Files:**
- `app.py` - New template and API endpoints

**New Directories:**
- `static/css/` - Stylesheets
- `static/images/` - Icons and graphics
- `static/fonts/` - Font files (YOU NEED TO ADD THESE!)

### 3. New API Endpoint
- `/api/get_user_accounts` - Fetches accounts owned by a specific username from Salesforce

## What You Need To Do

### 1. Replace the Q Icon ✨
1. Upload your actual Q character icon
2. Replace `/Users/tws/Desktop/NZOH/nzoh-programs/B2B-insights/simple_report_app/static/images/q-icon.svg`
3. Recommended format: SVG (scalable) or PNG (high resolution)
4. Recommended size: 80x80px or larger

### 2. Add Rale Grotesk Fonts 📝
You need to add these font files to `static/fonts/`:

- `RaleGrotesk-Regular.woff2`
- `RaleGrotesk-RegularItalic.woff2`
- `RaleGrotesk-Thin.woff2`
- `RaleGrotesk-ThinItalic.woff2`
- `RaleGrotesk-Medium.woff2`
- `RaleGrotesk-Black.woff2`
- `RaleGrotesk-BlackItalic.woff2`

**Font Usage Map:**
- **Q Character**: Black Italic (900 weight, italic)
- **User Input**: Regular Italic (400 weight, italic)
- **Domain (@novozymes.com)**: Thin Italic (100 weight, italic)
- **Buttons**: Regular Italic (400 weight, italic)
- **Account Names**: Medium (500 weight)
- **Messages**: Regular Italic (400 weight, italic)

### 3. If Fonts Aren't Available
If you can't get the Rale Grotesk fonts immediately, the page will fall back to system fonts (it won't break). The CSS already has fallbacks:

```css
font-family: 'Rale Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

## Features Implemented

### ✅ User Experience
- **Remembers initials**: Uses `localStorage` to remember returning users
- **Dynamic account loading**: Queries Salesforce for accounts owned by entered username
- **Smooth transitions**: Fade in/out animations between steps
- **Rotating Q icon**: During report generation
- **2-second hold**: On completion screen before redirect
- **Welcome back**: Different greeting for returning users

### ✅ Technical Features
- **State management**: Tracks user through multi-step flow
- **Dropdown interaction**: Click to open/close, select account
- **Hover states**: Visual feedback on account options
- **Disabled states**: Next buttons disabled until required input
- **Error handling**: Graceful fallbacks if API calls fail
- **Responsive design**: Works on different screen sizes

## User Flow

```
Step 1: Enter Initials
   ↓
   [Saved to localStorage]
   ↓
Step 2: Select Account
   ↓
   [Query Salesforce for user's accounts]
   ↓
   [User selects an account]
   ↓
Step 3: Generating Report
   ↓
   [Q icon rotates, "This'll take a few seconds..."]
   ↓
Step 4: Report Complete
   ↓
   [Hold for 2 seconds]
   ↓
   [Auto-redirect to /results]
   ↓
   [Or press "back" to make another report]
```

## Customization Options

### Colors
Main blue color is defined throughout `landing.css`:
```css
background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
```

You can change this gradient or use a solid color if preferred.

### Animations
- Q rotation: 2 seconds per full rotation
- Transitions: 0.5 seconds fade in/out
- Completion hold: 2 seconds before redirect

All timings can be adjusted in `app.py` and `landing.css`.

### Messages
All text is in the HTML template in `app.py` starting at line 46. Easy to customize:
- "Hi, I'm Q"
- "What are your initials?"
- "Welcome, {initials}!" / "Welcome back, {initials}!"
- "Who needs our attention?"
- "Ok, I'll get on that report"
- "This'll take a few seconds..."
- "Press 'back' if I can make another report for you"

## Testing

1. **Start the app**: `python app.py`
2. **Enter test initials**: Try "tws" or any username that owns accounts in Salesforce
3. **Check account dropdown**: Should populate with real accounts from Salesforce
4. **Generate report**: Select an account and generate
5. **Test back button**: After report completes, test the "back" functionality
6. **Test returning user**: Refresh page - should remember your initials

## Troubleshooting

### Fonts Not Loading
- Check that font files are in `static/fonts/` directory
- Check browser console for 404 errors
- Verify font file names match exactly in `landing.css`

### Q Icon Not Showing
- Check that file exists at `static/images/q-icon.svg`
- Check browser console for errors
- Verify Flask route `/static/images/q-icon.svg` is working

### Accounts Not Loading
- Check browser console for API errors
- Verify username exists in Salesforce
- Check Salesforce credentials in `app.py`
- Test endpoint: `POST /api/get_user_accounts` with `{"username": "tws"}`

### Styling Issues
- Check that `landing.css` is loading: `/static/css/landing.css`
- Clear browser cache (Cmd+Shift+R or Ctrl+F5)
- Check browser console for CSS errors

## Next Steps

1. Upload Q icon
2. Add Rale Grotesk fonts
3. Test the entire flow
4. Customize colors/text if needed
5. Deploy!

The landing page is fully functional and ready to use once you add the Q icon and fonts. Even without the fonts, it will work with fallback system fonts.

