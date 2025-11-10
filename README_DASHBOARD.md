# Sales Dashboard - Vue.js Implementation

This dashboard has been updated to match the mockup design with the following features:

## Design Features

### Left Panel (Dark Blue)
- **Account Header**: Displays account name and date range
- **Status Gauge**: Shows account status with horizontal progress bar
  - Calculated as (BB% + RSI) / 2
  - Status text: Understocked, Low Stock, Balanced, or Overstocked
- **90-Day Budgets**: Shows spending targets
  - Shrinking (Conservative)
  - Balanced
  - Trending (Aggressive)
  - Trailing 90-Day Budget

### Right Panel (White)
- **Order Recommendations**: Main title
- **Top Performers Section** (Green accent)
  - Products with gauge values ≥ 60%
  - Shows up to 3 products
  - Green progress bars
- **Low Stock Section** (Pink accent)
  - Products with gauge values ≤ 40%
  - Shows up to 2 products
  - Pink progress bars

## Product Display Features

Each product shows:
- **Product Image**: Uploaded images with fallback to placeholder
- **Product Name**: In uppercase
- **Ranking**: Based on priority (e.g., "#1 seller in 60ct")
- **Progress Bar**: Visual representation of gauge value
- **Recommendations**: Trending and Balanced quantities with values
- **Delivery Date**: Formatted as "by MM/DD"

## Data Sources

### Text Report Parsing
- **RSI Signal**: Extracted from "RSI Signal (XX.X)" pattern
- **Bollinger Band Position**: Extracted from "Current Position in Bollinger Band: XX.X%"
- **Product Data**: Parsed from ORDER WEEK sections
- **Recommendations**: Conservative, Balanced, and Aggressive values

### Gauge Calculations
- **Account Gauge**: (BB Position + RSI) / 2
- **Product Gauges**: Calculated from position bar strings (||--x--||)

## Image Management

### Uploading Product Images
```python
from indicators_report import upload_product_image

# Upload an image for a product
upload_product_image("MegaSporeBiotic", "/path/to/image.jpg")
```

### Image Naming Convention
- Images are stored in `images/` directory
- Filename format: `product_name_lowercase_with_underscores.jpg`
- Example: `MegaSporeBiotic` → `megasporebiotic.jpg`

### Available Functions
- `upload_product_image(product_name, image_path)`: Upload a product image
- `get_product_image_path(product_name)`: Get image path for a product
- `list_available_product_images()`: List all available product images

## Usage

1. **Generate Report**: Run your indicators_report.py to generate text reports
2. **Upload Images**: Use the upload functions to add product images
3. **Generate Dashboard**: The sales_dashboard.py will automatically create the Vue.js dashboard
4. **View Dashboard**: Open the generated HTML file in a web browser

## File Structure

```
simple_report_app/
├── vue_dashboard.html          # Vue.js dashboard template
├── sales_dashboard.py          # Dashboard data parsing and generation
├── indicators_report.py        # Main report generation with image functions
├── upload_product_images.py    # Example image upload script
├── images/                     # Product images directory
│   ├── megasporebiotic.jpg
│   ├── megamucosa.jpg
│   └── ...
└── README_DASHBOARD.md         # This file
```

## Styling

The dashboard uses:
- **Dark Blue Gradient**: Left panel background
- **White**: Right panel background
- **Green**: Top performers accent color (#22c55e)
- **Pink**: Low stock accent color (#f87171)
- **Modern Typography**: System fonts with proper hierarchy
- **Responsive Design**: Flexbox layout with proper spacing

## Browser Compatibility

- Modern browsers with CSS Grid and Flexbox support
- CSS Custom Properties (CSS Variables) support
- No external dependencies required
