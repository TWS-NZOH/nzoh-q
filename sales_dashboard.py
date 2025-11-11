"""
Sales Dashboard - Simplified interface for sales team
Creates a clean, actionable dashboard with gauges and simplified data
"""

import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

def parse_sales_dashboard_data(text_report: str) -> Dict[str, Any]:
    """
    Parse the text report to extract data for the sales dashboard
    """
    data = {
        'account_gauge_value': 0,
        'account_gauge_status': '',
        'conservative_spend': 0,
        'balanced_spend': 0, 
        'trending_spend': 0,
        'avg_spend': 0,
        'products': [],
        'order_timeline': [],
        'primary_week': {'weekNum': 0, 'conservative': 0, 'trending': 0},
        'key_products': [],
        'total_conservative': 0,
        'total_trending': 0,
        'total_products': 0,
        'total_weeks': 0,
        'date_range': ''
    }
    
    # Extract date range from "Generated on" date and calculate 90-day backward range
    generated_match = re.search(r'Generated on: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', text_report)
    if generated_match:
        generated_date = datetime.strptime(generated_match.group(1), '%Y-%m-%d %H:%M:%S')
        end_date = generated_date
        start_date = end_date - timedelta(days=90)
        data['date_range'] = f"{start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}"
    
    # Extract account gauge value (BB position + RSI) / 2
    bb_match = re.search(r'Current Position in Bollinger Band: ([\d.]+)%', text_report)
    rsi_match = re.search(r'RSI Signal \(([\d.]+)\)', text_report)
    
    if bb_match and rsi_match:
        bb_position = float(bb_match.group(1))
        rsi_value = float(rsi_match.group(1))
        data['account_gauge_value'] = round((bb_position + rsi_value) / 2, 1)
        data['account_gauge_status'] = get_gauge_status(data['account_gauge_value'])
    
    # Extract spend values from TARGET ACCOUNT SPEND section
    conservative_match = re.search(r'Conservative:\s+\$([\d,]+\.?\d*)', text_report)
    balanced_match = re.search(r'Balanced:\s+\$([\d,]+\.?\d*)', text_report)
    aggressive_match = re.search(r'Aggressive:\s+\$([\d,]+\.?\d*)', text_report)
    trailing_match = re.search(r'Trailing 90-Day Average:\s+\$([\d,]+\.?\d*)', text_report)
    
    if conservative_match:
        data['conservative_spend'] = float(conservative_match.group(1).replace(',', ''))
    if balanced_match:
        data['balanced_spend'] = float(balanced_match.group(1).replace(',', ''))
    if aggressive_match:
        data['trending_spend'] = float(aggressive_match.group(1).replace(',', ''))
    if trailing_match:
        data['avg_spend'] = float(trailing_match.group(1).replace(',', ''))
    
    # Parse products and timeline
    data.update(parse_products_and_timeline(text_report))
    
    return data

def get_gauge_status(value: float) -> str:
    """Get status text based on gauge value with new categories
    Note: For account-level assessment, we cap at 'well stocked'
    Individual products can still be classified as overstocked
    """
    if value < 50:
        return 'understocked'
    elif value < 65:
        return 'stocked'
    else:
        # Cap at 'well stocked' for account-level assessment
        return 'well stocked'

def generate_account_description(account_name: str, products: List[Dict], gauge_status: str, balanced_spend: float, trending_spend: float) -> str:
    """Generate the descriptive text for the blue panel"""
    
    # Filter out products with no data
    valid_products = [p for p in products if p.get('gaugeValue') is not None]
    
    if not valid_products:
        return f"{account_name} is generally {gauge_status}. We're analyzing their product portfolio."
    
    # Classify products as low stock (below 50%), top performers (by priority), overstocked (>70%)
    low_stock_products = [p for p in valid_products if p.get('gaugeValue', 50) < 50]
    top_performers = sorted(valid_products, key=lambda p: p.get('priority', 999))[:max(1, len(valid_products) // 5)]  # Top 20%
    overstocked_products = [p for p in valid_products if p.get('gaugeValue', 50) > 70]
    
    # Top performers that are also low stock
    top_performers_low_stock = [p for p in top_performers if p.get('gaugeValue', 50) < 50]
    
    # Low stock products that are NOT top performers
    low_stock_not_top = [p for p in low_stock_products if p not in top_performers_low_stock]
    
    # Calculate costs using balancedValue
    cost_top_performers = sum(float(p.get('balancedValue', 0)) for p in top_performers_low_stock)
    cost_all_low_stock = sum(float(p.get('balancedValue', 0)) for p in low_stock_products)
    cost_low_stock_without_top = cost_all_low_stock - cost_top_performers
    
    # Build the description
    description_parts = []
    
    # First paragraph - new format
    len_low_stock = len(low_stock_products)
    len_top_performers_low = len(top_performers_low_stock)
    
    if len_top_performers_low > 0:
        top_performer_names = ", ".join([p.get('name', 'Unknown') for p in top_performers_low_stock])
        description_parts.append(
            f"{account_name} is generally {gauge_status}. Let's focus on {len_low_stock} products they might not have enough of. "
            f"Note these include {len_top_performers_low} of their top performers ({top_performer_names})."
        )
    else:
        description_parts.append(
            f"{account_name} is generally {gauge_status}. Let's focus on {len_low_stock} products they might not have enough of."
        )
    
    # Second paragraph - suggestions for top performers (without the out-of-stock note)
    if len_top_performers_low >= 1:
        top_suggestions = []
        for i, p in enumerate(top_performers_low_stock[:3]):  # Show up to 3
            units = p.get('balanced', 0)
            top_suggestions.append(f"{units} units {p.get('name', 'Unknown')}")
        
        if len(top_suggestions) > 1:
            suggestions_text = ", ".join(top_suggestions[:-1]) + f", and {top_suggestions[-1]}"
        else:
            suggestions_text = top_suggestions[0] if top_suggestions else ""
        
        if suggestions_text:
            description_parts.append(
                f"I suggest {suggestions_text}."
            )
    
    # Third paragraph - cost breakdown (updated format, exclude top performers from list)
    if cost_top_performers > 0:
        description_parts.append(
            f"This would be ${cost_top_performers:,.2f}."
        )
        
        low_after_top = balanced_spend - cost_top_performers
        high_after_top = trending_spend - cost_top_performers
        
        # Only list low stock items that are NOT top performers
        low_stock_not_top_names = [p.get('name', 'Unknown') for p in sorted(low_stock_not_top, key=lambda p: p.get('priority', 999))]
        
        if len(low_stock_not_top_names) > 0:
            low_stock_list = ", ".join(low_stock_not_top_names[:10])  # First 10
            if len(low_stock_not_top_names) > 10:
                low_stock_list += f", and {len(low_stock_not_top_names) - 10} more"
            
            description_parts.append(
                f"That leaves ${low_after_top:,.2f} - ${high_after_top:,.2f} of 90-day projected spend, and there's low stock of:<br>{low_stock_list}."
            )
    
    # Fourth paragraph - non-top-performer low stock
    if cost_low_stock_without_top > 0:
        description_parts.append(
            f"${cost_low_stock_without_top:,.2f} brings these to healthy levels."
        )
    
    # Fifth paragraph - overstocked items (updated language)
    if len(overstocked_products) > 0:
        overstocked_names = ", ".join([p.get('name', 'Unknown') for p in overstocked_products[:5]])
        description_parts.append(
            f"They have a lot of {overstocked_names}. Check if these have been sitting on their shelf or if there's a new wave of interest behind the higher than average quantities."
        )
    
    # Final summary
    description_parts.append(
        f"Order just top performers: ${cost_top_performers:,.2f}"
    )
    description_parts.append(
        f"Order all low stock: ${cost_all_low_stock:,.2f}"
    )
    
    # Add the out-of-stock note at the end
    description_parts.append(
        f"If anything has been out of stock for a week or more, {account_name} may want my middle suggestion for those products to account for outstanding demand."
    )
    
    return "<br><br>".join(description_parts)

def parse_products_and_timeline(text_report: str) -> Dict[str, Any]:
    """Parse products and order timeline from the report"""
    
    # Extract product data from the report
    products = []
    order_timeline = []
    
    # Find all product sections with improved regex
    product_sections = re.findall(r'ORDER WEEK: ([\d.]+) - ([\d.]+)\s+Value Range: \[\$([\d,]+\.?\d*) < \$([\d,]+\.?\d*) < \$([\d,]+\.?\d*)\]\s+Products Due: (\d+)\s+(.*?)(?=ORDER WEEK:|$)', text_report, re.DOTALL)
    
    week_num = 1
    for week_data in product_sections:
        start_date, end_date, conservative, balanced, trending, product_count, products_text = week_data
        
        # Parse individual products in this week with improved regex
        week_products = []
        product_matches = re.findall(r'([A-Za-z0-9\s]+?)\s+Priority: (\d+)\s+Next Order Due: ([\d.]+)\s+Current Position:\s+([|x-]+)\s+Floor.*?Order Recommendations:\s+(.*?)(?=\s+[A-Za-z0-9\s]+\s+Priority:|\s*$)', products_text, re.DOTALL)
        
        for product_match in product_matches:
            product_name, priority, next_order, position_bar, recommendations = product_match
            
            # Parse recommendations with correct labels (conservative, balanced, aggressive)
            conservative_match = re.search(r'Conservative: (?:(\d+) units \(\$([\d,]+\.?\d*)\)|Maintain current position)', recommendations)
            balanced_match = re.search(r'Balanced: (?:(\d+) units \(\$([\d,]+\.?\d*)\)|At or above average)', recommendations)
            aggressive_match = re.search(r'Aggressive: (?:(\d+) units \(\$([\d,]+\.?\d*)\)|At upper target)', recommendations)
            
            # Calculate gauge value from position bar (BB% + RSI / 2)
            gauge_value = calculate_gauge_from_position_bar(position_bar)
            
            product_data = {
                'name': product_name.strip(),
                'priority': int(priority),
                'nextOrder': next_order,
                'positionBar': position_bar.strip(),
                'gaugeValue': gauge_value,
                'conservative': int(conservative_match.group(1)) if conservative_match and conservative_match.group(1) else 0,
                'balanced': int(balanced_match.group(1)) if balanced_match and balanced_match.group(1) else 0,
                'aggressive': int(aggressive_match.group(1)) if aggressive_match and aggressive_match.group(1) else 0,
                'conservativeValue': float(conservative_match.group(2).replace(',', '')) if conservative_match and conservative_match.group(2) else 0,
                'balancedValue': float(balanced_match.group(2).replace(',', '')) if balanced_match and balanced_match.group(2) else 0,
                'aggressiveValue': float(aggressive_match.group(2).replace(',', '')) if aggressive_match and aggressive_match.group(2) else 0
            }
            
            
            week_products.append(product_data)
            
            # Add to products list if not already there (with full data for description generation)
            if not any(p['name'] == product_data['name'] for p in products):
                products.append({
                    'name': product_data['name'],
                    'gaugeValue': gauge_value,
                    'priority': product_data['priority'],
                    'balanced': product_data['balanced'],
                    'balancedValue': product_data['balancedValue'],
                    'conservative': product_data['conservative'],
                    'conservativeValue': product_data['conservativeValue'],
                    'aggressive': product_data['aggressive'],
                    'aggressiveValue': product_data['aggressiveValue']
                })
        
        # Add week to timeline
        week_data = {
            'weekNum': week_num,
            'dates': f"{start_date} - {end_date}",
            'conservative': float(conservative.replace(',', '')),
            'balanced': float(balanced.replace(',', '')),
            'aggressive': float(trending.replace(',', '')),
            'productCount': int(product_count),
            'expanded': False,
            'products': week_products
        }
        
        order_timeline.append(week_data)
        week_num += 1
    
    # Find primary focus week
    primary_week = {'weekNum': 0, 'conservative': 0, 'aggressive': 0}
    if order_timeline:
        # Find week with highest balanced value
        primary_week = max(order_timeline, key=lambda x: x['balanced'])
    
    # Extract key products from recommended actions
    key_products = []
    key_products_match = re.search(r'Key Products to Focus:\s+(.*?)(?=\n\n|\nTotal|\nRECOMMENDED|\n$)', text_report, re.DOTALL)
    if key_products_match:
        key_products_text = key_products_match.group(1)
        key_products = [line.strip().replace('- ', '') for line in key_products_text.split('\n') if line.strip()]
    
    # Calculate totals
    total_conservative = sum(week['conservative'] for week in order_timeline)
    total_aggressive = sum(week['aggressive'] for week in order_timeline)
    total_products = sum(week['productCount'] for week in order_timeline)
    total_weeks = len(order_timeline)
    
    return {
        'products': products,
        'order_timeline': order_timeline,
        'primary_week': primary_week,
        'key_products': key_products,
        'total_conservative': int(total_conservative),
        'total_aggressive': int(total_aggressive),
        'total_products': total_products,
        'total_weeks': total_weeks
    }

def calculate_gauge_from_position_bar(position_bar: str) -> int:
    """Calculate gauge value from position bar string"""
    # Count total characters and find position of 'x'
    total_chars = len(position_bar)
    x_position = position_bar.find('x')
    
    if x_position == -1:
        return 50  # Default to middle if no 'x' found
    
    # Convert position to percentage
    return int((x_position / total_chars) * 100)


def get_product_image_path(product_name: str) -> str:
    """Get the image path for a product, checking for both jpg and png formats"""
    from pathlib import Path
    import re
    
    # Convert product name to filename format - sanitize to match Vue dashboard logic
    filename = product_name.lower().replace(' ', '_').replace('-', '_')
    filename = re.sub(r'[^a-z0-9_]', '', filename)  # Remove any special characters
    
    # Check for both jpg and png files
    images_dir = Path(__file__).parent / "images"
    jpg_path = images_dir / f"{filename}.jpg"
    png_path = images_dir / f"{filename}.png"
    
    # Return the path that exists, defaulting to jpg if neither exists
    if png_path.exists():
        return f"images/{filename}.png"
    elif jpg_path.exists():
        return f"images/{filename}.jpg"
    else:
        # Default to jpg if neither file exists (for fallback behavior)
        return f"images/{filename}.jpg"

def create_sales_dashboard_html(account_name: str, dashboard_data: Dict[str, Any], account_id: str = "", generated_time: str = "", base_url: str = "", owner_email: str = "unknown@novozymes.com") -> str:
    """Create the HTML for the Vue.js sales dashboard"""
    import json
    import sys
    import os
    
    # Read the Vue.js template
    # Handle PyInstaller path resolution
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller executable
        meipass = Path(sys._MEIPASS)
        template_path = meipass / "vue_dashboard.html"
        
        # Debug: List files in _MEIPASS if file not found
        if not template_path.exists():
            try:
                files_in_meipass = list(meipass.iterdir())
                print(f"Debug: Files in _MEIPASS ({meipass}): {[f.name for f in files_in_meipass[:20]]}")
            except:
                pass
    else:
        # Running from source
        template_path = Path(__file__).parent / "vue_dashboard.html"
    
    if not template_path.exists():
        # Try alternative locations
        alternative_paths = [
            Path(__file__).parent.parent / "vue_dashboard.html",  # One level up
            Path.cwd() / "vue_dashboard.html",  # Current working directory
        ]
        
        for alt_path in alternative_paths:
            if alt_path.exists():
                template_path = alt_path
                break
        else:
            raise FileNotFoundError(
                f"vue_dashboard.html not found at {template_path}\n"
                f"Tried: {[str(template_path)] + [str(p) for p in alternative_paths]}"
            )
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Add image paths to products
    for product in dashboard_data['products']:
        image_path = get_product_image_path(product['name'])
        if base_url:
            image_path = f"{base_url.rstrip('/')}/{image_path}"
        product['imagePath'] = image_path
    
    # Add image paths to order timeline products
    for week in dashboard_data['order_timeline']:
        for product in week['products']:
            image_path = get_product_image_path(product['name'])
            if base_url:
                image_path = f"{base_url.rstrip('/')}/{image_path}"
            product['imagePath'] = image_path
    
    # Generate account description with calculated variables
    account_description = generate_account_description(
        account_name=account_name,
        products=dashboard_data['products'],
        gauge_status=dashboard_data['account_gauge_status'],
        balanced_spend=dashboard_data['balanced_spend'],
        trending_spend=dashboard_data['trending_spend']
    )
    
    # Replace template variables with actual data
    html = template.replace('ACCOUNT_NAME_PLACEHOLDER', account_name)
    html = html.replace('ACCOUNT_ID_PLACEHOLDER', account_id)
    html = html.replace('GENERATED_TIME_PLACEHOLDER', generated_time)
    html = html.replace('OWNER_EMAIL_PLACEHOLDER', owner_email)
    html = html.replace('DATE_RANGE_PLACEHOLDER', dashboard_data.get('date_range', '6/6/25 - 9/4/25'))
    html = html.replace('ACCOUNT_GAUGE_VALUE_PLACEHOLDER', str(dashboard_data['account_gauge_value']))
    html = html.replace('ACCOUNT_GAUGE_STATUS_PLACEHOLDER', dashboard_data['account_gauge_status'])
    html = html.replace('CONSERVATIVE_SPEND_PLACEHOLDER', str(dashboard_data['conservative_spend']))
    html = html.replace('BALANCED_SPEND_PLACEHOLDER', str(dashboard_data['balanced_spend']))
    html = html.replace('TRENDING_SPEND_PLACEHOLDER', str(dashboard_data['trending_spend']))
    html = html.replace('AVG_SPEND_PLACEHOLDER', str(dashboard_data['avg_spend']))
    
    # Replace the account description placeholder
    html = html.replace('ACCOUNT_DESCRIPTION_PLACEHOLDER', account_description)
    html = html.replace('PRODUCTS_PLACEHOLDER', json.dumps(dashboard_data['products']))
    html = html.replace('ORDER_TIMELINE_PLACEHOLDER', json.dumps(dashboard_data['order_timeline']))
    html = html.replace('PRIMARY_WEEK_PLACEHOLDER', json.dumps(dashboard_data['primary_week']))
    html = html.replace('KEY_PRODUCTS_PLACEHOLDER', json.dumps(dashboard_data['key_products']))
    html = html.replace('TOTAL_CONSERVATIVE_PLACEHOLDER', str(dashboard_data['total_conservative']))
    html = html.replace('TOTAL_TRENDING_PLACEHOLDER', str(dashboard_data['total_aggressive']))
    html = html.replace('TOTAL_PRODUCTS_PLACEHOLDER', str(dashboard_data['total_products']))
    html = html.replace('TOTAL_WEEKS_PLACEHOLDER', str(dashboard_data['total_weeks']))
    
    return html

