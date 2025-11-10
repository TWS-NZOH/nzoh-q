# Pricebook Pricing Update

## Overview
Updated the system to use **current Pricebook prices** instead of historical OrderItem.UnitPrice averages for calculating suggested order values.

## Changes Made

### 1. New Function: `get_pricebook_prices()`
**Location**: `indicators_report.py` (lines ~574-637)

**Purpose**: Queries Salesforce PricebookEntry to get current unit prices for products

**How it works**:
- Fetches the Standard Pricebook ID from Salesforce
- Queries all PricebookEntry records for the given Product2Ids
- Returns a dictionary mapping Product2Id → current UnitPrice
- Reports which products were found vs. not found in the pricebook

**Example output**:
```
🔍 Fetching pricebook prices for 15 products...
  Using Standard Pricebook: 01s2j000000ABCD
  ✓ MegaSporeBiotic: $59.99
  ✓ Total Gut Restore: $89.99
  ✓ HU58: $49.99
  ⚠️  2 products not found in pricebook (will use historical prices)
  ✓ Found pricebook prices for 13/15 products
```

### 2. Updated Function: `create_product_ohlcv()`
**Location**: `indicators_report.py` (lines ~480-572)

**Changes**:
- Added new parameter: `pricebook_prices=None`
- Logic now checks if pricebook price exists for the product
- **If pricebook price found**: Uses that consistent price for all calculations
- **If not found**: Falls back to historical OrderItem.UnitPrice averaging

**Example output per product**:
```
Processing product: MegaSporeBiotic
    Using pricebook price: $59.99
```
or
```
Processing product: Legacy Product XYZ
    Using historical average price: $45.23
```

### 3. Updated Analysis Flow
**Location**: `indicators_report.py` (lines ~1110-1125 and ~3710-3725)

**Changes**:
- After fetching products, immediately queries pricebook prices
- Passes `pricebook_prices` dictionary to all `create_product_ohlcv()` calls

**Code flow**:
```python
products = get_account_products(...)
order_products = get_account_order_products(...)

# NEW: Fetch pricebook prices
pricebook_prices = get_pricebook_prices(list(products.keys()))

# Pass pricebook prices to product analysis
for product_id, product_name in products.items():
    df = create_product_ohlcv(order_products, product_id, resolution, ma_window, pricebook_prices)
```

## Benefits

### ✅ Consistent Pricing
- All suggested orders now use current, official pricebook prices
- No more averaging of historical prices that may have changed over time

### ✅ Accurate Order Values
- Conservative/Balanced/Aggressive order suggestions show correct dollar amounts
- Week-by-week order timeline totals are accurate

### ✅ Graceful Fallback
- Products not in pricebook still work (uses historical average)
- No breaking changes if pricebook query fails

### ✅ Transparent Logging
- Clear console output showing which price source is used for each product
- Easy to identify products missing from pricebook

## Impact on Reports

### Before (Historical Averaging)
```
MegaSporeBiotic
   Order Recommendations:
      Conservative: 50 units ($2,750.00)    ← Mixed historical prices $45-$65
      Balanced: 100 units ($5,500.00)
      Aggressive: 150 units ($8,250.00)
```

### After (Pricebook Pricing)
```
MegaSporeBiotic
   Order Recommendations:
      Conservative: 50 units ($2,999.50)    ← Consistent $59.99 pricebook price
      Balanced: 100 units ($5,999.00)
      Aggressive: 150 units ($8,998.50)
```

## Testing

### To verify the changes are working:

1. **Run a report for any account**:
   ```bash
   cd simple_report_app
   python indicators_report.py
   ```

2. **Look for pricebook pricing output**:
   ```
   🔍 Fetching pricebook prices for X products...
   ```

3. **Check each product shows its price source**:
   ```
   Processing product: [Product Name]
       Using pricebook price: $XX.XX
   ```
   or
   ```
   Processing product: [Product Name]
       Using historical average price: $XX.XX
   ```

4. **Verify suggestions use correct prices**:
   - Check the HTML/text report product recommendations
   - Multiply unit quantity by the pricebook price shown
   - Should match the dollar value in parentheses

### Example Test Case
For **MegaSporeBiotic** with pricebook price **$59.99**:
- If recommendation is "100 units"
- Dollar value should show: "($5,999.00)"
- Calculation: 100 × $59.99 = $5,999.00 ✓

## Troubleshooting

### Products showing historical prices instead of pricebook
**Cause**: Product not found in Standard Pricebook

**Solution**: 
1. Check if product exists in Salesforce Pricebook2
2. Verify PricebookEntry is marked as `IsActive = true`
3. Ensure Product2Id matches between OrderItem and Pricebook

### Pricebook query fails
**Cause**: Standard Pricebook not found or API error

**Behavior**: System automatically falls back to historical pricing for all products

**Check**: Console output will show:
```
⚠️  Warning: No standard pricebook found, falling back to historical prices
```

### Wrong pricebook being used
**Current**: System uses the Standard Pricebook (IsStandard = true)

**Future Enhancement**: Could be updated to check account-specific pricebooks first, then fall back to standard pricebook.

## Technical Notes

### Why Pricebook Pricing is Better

1. **Historical prices can vary**:
   - Customer may have received promotional pricing
   - Prices may have changed over time
   - Volume discounts may have applied to some orders
   - Result: Inconsistent averages

2. **Pricebook prices are official**:
   - Single source of truth
   - Reflects current pricing strategy
   - Easy to update in Salesforce if prices change

3. **Better for forecasting**:
   - Future orders will use current prices
   - More accurate revenue projections
   - Aligns with actual invoicing

### Data Flow
```
Salesforce
  ├─ OrderItem (historical orders)
  │    └─ Used for: Quantity trends, buying patterns
  │
  └─ PricebookEntry (current prices)
       └─ Used for: Unit price × quantity = suggested order value
```

## Future Enhancements

### Potential Improvements:
1. **Account-specific pricing**: Check for account-specific pricebook entries before standard pricebook
2. **Price alerts**: Notify if pricebook price differs significantly from recent historical average
3. **Multi-currency**: Support different currencies based on account location
4. **Volume pricing**: Use quantity breakpoints for tiered pricing
5. **Caching**: Cache pricebook prices to reduce API calls

## Migration Notes

### Backward Compatibility
✅ **Fully backward compatible**
- If `pricebook_prices` parameter is omitted, function uses historical prices (old behavior)
- No changes required to existing function calls
- Graceful degradation if pricebook query fails

### Performance Impact
- **+1 additional Salesforce query** per analysis (PricebookEntry query)
- Query returns results for all products at once (efficient bulk query)
- Minimal performance impact (< 1 second for typical accounts)

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Price Source** | OrderItem.UnitPrice averaged | PricebookEntry.UnitPrice |
| **Consistency** | Varies by order | Constant per product |
| **Accuracy** | Mixed historical prices | Current official prices |
| **Transparency** | Silent averaging | Logged per product |
| **Fallback** | N/A | Uses historical if pricebook unavailable |

---

**Last Updated**: October 13, 2025  
**Author**: AI Assistant  
**Version**: 1.0

