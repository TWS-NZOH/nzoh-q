# Product Name and Account Owner Email Fixes
**Date:** October 12, 2025

## Issues Fixed

### 1. Missing Product Names Issue
**Problem:** The #2 top-selling product had no name displayed. Products were appearing with missing names even though they had legitimate sales data.

**Root Cause:** The `get_account_order_products()` function only queried the `Product_Name__c` field from Salesforce, without any fallback options when this custom field was empty or null.

**Why It Was Still a Product:** 
- Sales are correlated using **`Product2Id`** (the unique product identifier), not the product name
- The product had valid `TotalPrice`, `Quantity`, and `UnitPrice` data
- It's definitely a real product, not something like sales tax (which wouldn't have a Product2Id)

**Solution:** Enhanced the Salesforce query in `get_account_order_products()` to include multiple name fields with a cascading fallback system:

```python
# Updated query to include all name fields
SELECT 
    Id,
    Order.MBL_Order_Shipped_Time__c,
    Order.TotalAmount,
    Product2Id,
    Product_Name__c,
    Product2.Name,           # Added
    Product2.ProductCode,    # Added
    Quantity,
    TotalPrice,
    UnitPrice
FROM OrderItem
```

**Fallback Logic:**
1. First try: `Product_Name__c` (custom field)
2. Second try: `Product2.Name` (standard product name)
3. Third try: `Product2.ProductCode` (product code)
4. Last resort: `f"Unknown Product ({product_id})"`

**Files Modified:** 
- `simple_report_app/indicators_report.py` - Updated both instances of `get_account_order_products()` function (lines ~415-468 and duplicate section)

---

### 2. Hardcoded Account Owner Email
**Problem:** The email "cyk@novozymes.com" was hardcoded in the dashboard HTML files, showing the same contact for all accounts regardless of who actually owns the account.

**Solution:** Implemented dynamic account owner email retrieval and display:

#### A. Created `get_account_info()` Function
Added new function in `indicators_report.py` to retrieve account owner information from Salesforce:

```python
def get_account_info(account_id):
    """
    Get account name and owner username
    Returns dict with 'name' and 'owner_username' keys
    """
    query = f"""
        SELECT Id, Name, Owner.Username FROM Account WHERE Id = '{account_id}'
    """
    account = sf.query_all(query)
    record = account['records'][0]
    
    owner_username = ''
    if record.get('Owner') and record['Owner'].get('Username'):
        owner_username = record['Owner']['Username']
    
    return {
        'name': record['Name'],
        'owner_username': owner_username
    }
```

**Files Modified:**
- `simple_report_app/indicators_report.py` - Added function after `get_account_name()` in both code sections

#### B. Updated Backend to Pass Owner Email
Modified `app.py` to retrieve and pass account owner email to the frontend:

```python
# Get account info (name and owner)
account_info = indicators_report.get_account_info(account_id)
account_name = account_info['name']
owner_username = account_info['owner_username']

# Construct owner email
owner_email = f"{owner_username}@novozymes.com" if owner_username else "unknown@novozymes.com"
```

The email is now:
- Passed to `create_sales_dashboard_html()` function
- Included in JSON response
- Stored in `current_analysis_result`

**Files Modified:**
- `simple_report_app/app.py` - Lines ~344-350, ~418-424, ~428-441

#### C. Updated Dashboard Function
Modified `sales_dashboard.py` to accept and use the owner email:

```python
def create_sales_dashboard_html(
    account_name: str, 
    dashboard_data: Dict[str, Any], 
    account_id: str = "", 
    generated_time: str = "", 
    base_url: str = "", 
    owner_email: str = "unknown@novozymes.com"  # Added parameter
) -> str:
    # ...
    html = html.replace('OWNER_EMAIL_PLACEHOLDER', owner_email)
```

**Files Modified:**
- `simple_report_app/sales_dashboard.py` - Lines ~216, ~244

#### D. Updated HTML Templates
Replaced hardcoded emails with dynamic placeholders:

**vue_dashboard.html:**
```html
<!-- Before -->
<div class="account-email">cyk@novozymes.com</div>

<!-- After -->
<div class="account-email">OWNER_EMAIL_PLACEHOLDER</div>
```

**test_optimized_dashboard.html:**
```html
<!-- Before -->
<div class="footer">cyk@novozymes.com</div>

<!-- After -->
<div class="footer">accountowner@novozymes.com</div>
```

**Files Modified:**
- `simple_report_app/vue_dashboard.html` - Line 341
- `simple_report_app/test_optimized_dashboard.html` - Line 257

---

## How It Works Now

### Product Name Resolution
1. When `get_account_order_products()` is called, it retrieves all three name fields from Salesforce
2. For each OrderItem record, the code checks fields in order: `Product_Name__c` → `Product2.Name` → `Product2.ProductCode`
3. The first non-empty field is used as the product name
4. If all fields are empty, it displays `"Unknown Product ({Product2Id})"`
5. Console logging shows which fallback was used for debugging

### Account Owner Email
1. When analysis runs, `get_account_info()` retrieves the account owner's username from Salesforce
2. The username is combined with "@novozymes.com" to create the full email
3. The email is passed through the entire pipeline: Backend → Dashboard Generator → HTML Template
4. The final dashboard displays the actual account owner's email instead of a hardcoded value

---

## Benefits

✅ **Product Names:** All products now show complete, accurate names even if custom fields are empty  
✅ **Sales Correlation:** Clarified that sales are linked by Product2Id, not name - missing names don't affect data integrity  
✅ **Dynamic Emails:** Each account now shows the correct owner contact information  
✅ **Better Debugging:** Console logging helps identify when fallbacks are used  
✅ **Future-Proof:** System handles incomplete Salesforce data gracefully  

---

## Testing

To verify the fixes work correctly:

1. **Test Product Names:**
   - Run analysis for any account with products
   - Verify all products show complete names
   - Check console for fallback notifications
   - The #2 seller should now have a proper name

2. **Test Account Owner Email:**
   - Run analysis for multiple accounts with different owners
   - Verify each dashboard shows the correct owner's email
   - Check that email format is `{username}@novozymes.com`

3. **Test Fallback Scenarios:**
   - For products with empty Product_Name__c, verify Product2.Name is used
   - For accounts with no owner, verify "unknown@novozymes.com" appears

---

## Files Changed Summary

1. **simple_report_app/indicators_report.py**
   - Added `get_account_info()` function (2 instances)
   - Updated `get_account_order_products()` query and fallback logic (2 instances)

2. **simple_report_app/app.py**
   - Modified `analyze_account()` to use `get_account_info()`
   - Added owner_email to function calls and JSON responses

3. **simple_report_app/sales_dashboard.py**
   - Added `owner_email` parameter to `create_sales_dashboard_html()`
   - Added placeholder replacement for owner email

4. **simple_report_app/vue_dashboard.html**
   - Replaced hardcoded email with `OWNER_EMAIL_PLACEHOLDER`

5. **simple_report_app/test_optimized_dashboard.html**
   - Updated hardcoded email to generic placeholder for test purposes

---

## API Changes

The `/api/analyze` endpoint now returns additional data:

```json
{
    "success": true,
    "account_id": "0012j00000VutSnAAJ",
    "account_name": "Be Optimal",
    "owner_email": "cyk@novozymes.com",  // NEW
    "message": "Analysis completed successfully"
}
```

