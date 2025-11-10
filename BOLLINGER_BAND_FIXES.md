# Bollinger Band Percentile and Product Name Fixes
**Date:** October 12, 2025

## Issues Fixed

### 1. Product Name Retrieval Issue
**Problem:** Products were showing with missing or incomplete names (e.g., #2 seller had no name, products showing as "SLEEP" instead of "ZENBIOME SLEEP")

**Root Cause:** The Salesforce query in `get_account_products()` only retrieved `Product_Name__c` without fallback options when this field was empty or incomplete.

**Solution:** Enhanced the Salesforce query to include multiple name fields with a cascading fallback system:

```python
# Updated query to include all name fields
SELECT 
    Product2Id,
    Product_Name__c,
    Product2.Name,
    Product2.ProductCode
FROM OrderItem 
```

**Fallback Logic:**
1. First try: `Product_Name__c` (custom field)
2. Second try: `Product2.Name` (standard product name)
3. Third try: `Product2.ProductCode` (product code)
4. Last resort: `'Unknown Product'`

**Files Modified:** `simple_report_app/indicators_report.py` lines 517-560 and 2927-2970

---

### 2. Incorrect Bollinger Band Percentile Targets
**Problem:** The system was calculating unit recommendations targeting the wrong Bollinger Band percentiles:
- Was targeting: 0th (bb_lower), 50th (bb_middle), 100th (bb_upper)
- Should target: 50th (bb_middle), 70th percentile, 100th (bb_upper)

**Root Cause:** The quantity calculation used `bb_lower` for conservative recommendations instead of `bb_middle`, and didn't calculate the 70th percentile position.

**Solution:** Updated all quantity calculation calls to target the correct percentiles:

```python
# Target the correct percentile levels:
# Conservative = 50th percentile (bb_middle)
# Balanced = 70th percentile (between middle and upper)
# Aggressive = 100th percentile (bb_upper)
bb_70th = opp['bb_lower'] + (opp['bb_upper'] - opp['bb_lower']) * 0.7

cons_qty = calculate_target_quantity(opp, opp['bb_middle'])
bal_qty = calculate_target_quantity(opp, bb_70th)
agg_qty = calculate_target_quantity(opp, opp['bb_upper'])
```

**Updated Locations:**
1. Week summary calculations (lines ~806-816, ~3234-3244)
2. Individual product recommendations (lines ~844-857, ~3272-3285)
3. Week timeline creation (lines ~2177-2186, ~4605-4614)

---

## How Unit Price and Quantity Calculations Work

### Unit Price Source
1. Unit prices come from Salesforce `OrderItem.UnitPrice` field
2. Retrieved via `get_account_order_products()` query
3. Stored in the product OHLCV DataFrame as `unit_price` column
4. Used in opportunity analysis as `opp['unit_price']`

### Quantity Calculation Formula
The `calculate_target_quantity()` function calculates how many units are needed to bring the 3-day candle moving average to the target Bollinger Band level:

```python
def calculate_target_quantity(opp, target_value):
    current_value = opp['current_close']  # Current 3-day MA value
    
    if current_value >= target_value:
        return 0  # Already at or above target
    
    # Calculate value gap to target
    value_gap = target_value - current_value
    
    # Account for MA window (how much total order value needed)
    ma_window = 90  # 90-day moving average
    required_order_value = value_gap * ma_window
    
    # Convert to quantity using unit price
    quantity = required_order_value / opp['unit_price']
    
    return max(0, round(quantity))
```

### Example Calculation
If a product has:
- Current close: $1,000
- BB Middle (50th): $1,200
- BB 70th: $1,400
- BB Upper (100th): $1,600
- Unit price: $25

**Conservative (50th percentile):**
- Gap: $1,200 - $1,000 = $200
- Required order value: $200 × 90 = $18,000
- Units needed: $18,000 / $25 = **720 units**
- Total cost: 720 × $25 = **$18,000**

**Balanced (70th percentile):**
- Gap: $1,400 - $1,000 = $400
- Required order value: $400 × 90 = $36,000
- Units needed: $36,000 / $25 = **1,440 units**
- Total cost: 1,440 × $25 = **$36,000**

**Aggressive (100th percentile):**
- Gap: $1,600 - $1,000 = $600
- Required order value: $600 × 90 = $54,000
- Units needed: $54,000 / $25 = **2,160 units**
- Total cost: 2,160 × $25 = **$54,000**

---

## Testing Instructions

To verify the fixes work correctly:

1. **Test Product Names:**
   - Run analysis for Be Optimal account
   - Verify all products show complete names
   - Check that the #2 seller now has a proper name
   - Confirm names like "ZENBIOME SLEEP" appear in full, not just "SLEEP"

2. **Test Quantity Calculations:**
   - For products below healthy levels, verify:
     - Conservative recommendation brings to 50th percentile (middle of BB)
     - Balanced recommendation brings to 70th percentile
     - Aggressive recommendation brings to 100th percentile (upper BB)
   - Verify dollar values shown in parentheses match: `units × unit_price`

3. **Visual Dashboard Check:**
   - Product gauges should show arrows at 50%, 70%, and 100% positions
   - Unit counts and dollar values should align with report data

---

## Files Changed
- `simple_report_app/indicators_report.py`
  - Lines 517-560: Updated `get_account_products()` with name fallbacks (first instance)
  - Lines 2927-2970: Updated `get_account_products()` with name fallbacks (second instance)
  - Lines ~806-816: Updated percentile targets in week summary
  - Lines ~844-857: Updated percentile targets in product recommendations
  - Lines ~2177-2186: Updated percentile targets in week timeline
  - Lines ~3234-3244: Updated percentile targets in week summary (duplicate)
  - Lines ~3272-3285: Updated percentile targets in product recommendations (duplicate)
  - Lines ~4605-4614: Updated percentile targets in week timeline (duplicate)

---

## Impact
- ✅ All products will now show complete, accurate names
- ✅ Quantity recommendations will correctly target 50th, 70th, and 100th percentiles
- ✅ Dollar values will accurately reflect unit prices from Salesforce
- ✅ Dashboard visualization will correctly show recommendation arrows

