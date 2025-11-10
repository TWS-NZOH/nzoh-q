# Product Name Capture Fix
**Date:** October 12, 2025

## Issue
Product names were being truncated in the dashboard, showing only partial names like:
- "SLEEP" instead of "Zenbiome Sleep"
- "60" instead of "RestorFlora 60"  
- "CAPSULES" instead of "MegaSporeBiotic Capsules"

## Root Cause
The regex pattern was using **non-greedy matching** (`+?`) which stopped capturing too early when product names contained multiple words separated by spaces.

## Solution

### 1. Fixed Regex Pattern (`sales_dashboard.py` Line 98)

**Before:**
```python
# Non-greedy matching - stops at first space
product_matches = re.findall(r'\s+([^\n]+?)\s+Priority:...
```

**After:**
```python
# Greedy matching - captures entire line including all spaces
product_matches = re.findall(r'\s+([^\n]+)\s+Priority:...
```

The change from `([^\n]+?)` to `([^\n]+)` makes the regex capture **greedily**, ensuring it gets the entire product name line including all words and spaces.

### 2. Enhanced Salesforce Queries (`indicators_report.py`)

**Added ProductCode field** to both query functions (Lines 413, 556):
```sql
SELECT 
    Product2Id,
    Product_Name__c,
    Product2.Name,
    Product2.ProductCode  -- Added as additional fallback
FROM OrderItem
```

**Improved name selection logic** with cascade:
1. First try: `Product_Name__c` (custom field)
2. Second try: `Product2.Name` (standard product name)
3. Third try: `Product2.ProductCode` (product code)
4. Last resort: `'Unknown Product'`

Lines 425-449 in `get_account_order_products()`:
```python
# Build complete product names from available fields
for record in order_products['records']:
    product_name = record.get('Product_Name__c', '').strip()
    product2_name = ''
    product2_code = ''
    
    if record.get('Product2'):
        product2_name = record['Product2'].get('Name', '').strip()
        product2_code = record['Product2'].get('ProductCode', '').strip()
    
    # Use Product_Name__c if available and non-empty
    if product_name:
        final_name = product_name
    # Otherwise try Product2.Name
    elif product2_name:
        final_name = product2_name
        print(f"Info: Using Product2.Name for Product2Id {record['Product2Id']}: {final_name}")
    # Last resort: use ProductCode
    elif product2_code:
        final_name = product2_code
        print(f"Warning: Using ProductCode for Product2Id {record['Product2Id']}: {final_name}")
    else:
        final_name = 'Unknown Product'
        print(f"Warning: No name found for Product2Id {record['Product2Id']}")
    
    record['Product_Name__c'] = final_name
```

### 3. Added Debug Logging (`sales_dashboard.py` Line 107)

```python
print(f"Debug: Captured product name: '{product_name}' (Priority: {priority})")
```

This helps verify that full names are being captured from the text report.

## How It Works

### Text Report Format:
```
  RestorFlora 60
     Priority: 9
     Next Order Due: 2025.09.05
```

### Regex Capture Process:
1. `\s+` matches leading whitespace (2 spaces)
2. `([^\n]+)` **greedily** captures everything up to newline: "RestorFlora 60"
3. `\s+` matches newline + indentation
4. `Priority: (\d+)` matches the priority number

### Result:
✅ Full product name "RestorFlora 60" is captured
✅ All multi-word names with spaces are preserved
✅ Product names display correctly in dashboard

## Testing
When you regenerate a report, you should see in the console:
```
Debug: Captured product name: 'RestorFlora 60' (Priority: 9)
Debug: Captured product name: 'Zenbiome Sleep' (Priority: 11)
Debug: Captured product name: 'MegaSporeBiotic Gummies Kids 30CT' (Priority: 4)
```

And the dashboard will show the complete names instead of truncated versions.

## Files Modified
1. `simple_report_app/sales_dashboard.py` - Fixed regex and added debugging
2. `simple_report_app/indicators_report.py` - Enhanced product name retrieval with multiple fallbacks

