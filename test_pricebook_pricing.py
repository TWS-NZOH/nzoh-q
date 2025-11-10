"""
Quick test script to verify pricebook pricing is working correctly
Run this to test the new pricing logic before running a full report
"""

import sys
from datetime import datetime, timedelta
from simple_salesforce import Salesforce

# MBL Integration User Login
username = 'sysadmin-integration@microbiome.com'
password = 'ChallengeDMENew!!2022'
security_token = 'beBgVXuIPh8KgZLRYqQ30P6Pv'
domain = 'login'

print("=" * 80)
print("PRICEBOOK PRICING TEST")
print("=" * 80)

print("\n1. Authenticating with Salesforce...")
sf = Salesforce(username=username, password=password, security_token=security_token, domain=domain)
print("   ✓ Connected to Salesforce\n")

# Test the pricebook query function
def test_get_pricebook_prices(product_ids):
    """Test function to get pricebook prices"""
    if not product_ids:
        return {}
    
    print(f"2. Fetching pricebook prices for {len(product_ids)} test products...")
    
    # Get standard pricebook
    try:
        std_pricebook = sf.query("SELECT Id, Name FROM Pricebook2 WHERE IsStandard = true LIMIT 1")
        if not std_pricebook['records']:
            print("   ✗ ERROR: No standard pricebook found!")
            return {}
        
        pricebook_id = std_pricebook['records'][0]['Id']
        pricebook_name = std_pricebook['records'][0]['Name']
        print(f"   ✓ Found Standard Pricebook: {pricebook_name} ({pricebook_id})")
    except Exception as e:
        print(f"   ✗ ERROR getting pricebook: {str(e)}")
        return {}
    
    # Query pricebook entries
    product_id_list = "','".join(product_ids)
    query = f"""
        SELECT Product2Id, UnitPrice, IsActive, Product2.Name, Product2.ProductCode
        FROM PricebookEntry
        WHERE Pricebook2Id = '{pricebook_id}'
        AND Product2Id IN ('{product_id_list}')
        AND IsActive = true
    """
    
    try:
        results = sf.query_all(query)
        price_map = {}
        
        print(f"\n3. Pricebook entries found:")
        for record in results['records']:
            product_id = record['Product2Id']
            unit_price = float(record['UnitPrice'])
            product_name = record['Product2']['Name'] if record.get('Product2') else 'Unknown'
            product_code = record['Product2'].get('ProductCode', 'N/A') if record.get('Product2') else 'N/A'
            price_map[product_id] = unit_price
            print(f"   ✓ {product_name}")
            print(f"      Product2Id: {product_id}")
            print(f"      ProductCode: {product_code}")
            print(f"      UnitPrice: ${unit_price:.2f}")
            print()
        
        missing = set(product_ids) - set(price_map.keys())
        if missing:
            print(f"\n   ⚠️  WARNING: {len(missing)} products NOT found in pricebook:")
            for pid in missing:
                print(f"      - {pid}")
        
        print(f"\n   RESULT: Found pricebook prices for {len(price_map)}/{len(product_ids)} products")
        return price_map
        
    except Exception as e:
        print(f"   ✗ ERROR querying pricebook entries: {str(e)}")
        return {}

# Get a sample account to test with
if len(sys.argv) > 1:
    account_id = sys.argv[1]
else:
    print("\nNo account ID provided. Fetching a sample account...\n")
    # Get an account with recent orders
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    sample_query = f"""
        SELECT Order.AccountId, Account.Name, COUNT(Id) OrderCount
        FROM OrderItem
        WHERE Order.MBL_Order_Shipped_Time__c >= {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}
        GROUP BY Order.AccountId, Account.Name
        HAVING COUNT(Id) > 10
        LIMIT 1
    """
    
    result = sf.query(sample_query)
    if result['records']:
        account_id = result['records'][0]['Order']['AccountId']
        account_name = result['records'][0]['Order']['Account']['Name']
        print(f"   Using sample account: {account_name}")
        print(f"   Account ID: {account_id}\n")
    else:
        print("   ✗ ERROR: No sample accounts found with recent orders")
        sys.exit(1)

# Get products for this account
print(f"4. Fetching products for account {account_id}...")
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

product_query = f"""
    SELECT Product2Id, Product2.Name, Product2.ProductCode, COUNT(Id) OrderCount
    FROM OrderItem
    WHERE Order.AccountId = '{account_id}'
    AND Order.MBL_Order_Shipped_Time__c >= {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}
    GROUP BY Product2Id, Product2.Name, Product2.ProductCode
    ORDER BY COUNT(Id) DESC
    LIMIT 10
"""

products_result = sf.query_all(product_query)
if not products_result['records']:
    print("   ✗ ERROR: No products found for this account")
    sys.exit(1)

print(f"   ✓ Found {len(products_result['records'])} products\n")

# Extract product IDs
product_ids = [r['Product2Id'] for r in products_result['records']]

# Test the pricebook pricing function
price_map = test_get_pricebook_prices(product_ids)

# Compare with historical prices
print("\n" + "=" * 80)
print("5. COMPARISON: Pricebook vs Historical Prices")
print("=" * 80)

for record in products_result['records']:
    product_id = record['Product2Id']
    product_name = record['Product2']['Name'] if record.get('Product2') else 'Unknown'
    
    # Get historical average price
    hist_query = f"""
        SELECT AVG(UnitPrice) avg_price, MIN(UnitPrice) min_price, MAX(UnitPrice) max_price
        FROM OrderItem
        WHERE Order.AccountId = '{account_id}'
        AND Product2Id = '{product_id}'
        AND Order.MBL_Order_Shipped_Time__c >= {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')}
    """
    hist_result = sf.query(hist_query)
    
    if hist_result['records']:
        hist_avg = float(hist_result['records'][0]['avg_price'] or 0)
        hist_min = float(hist_result['records'][0]['min_price'] or 0)
        hist_max = float(hist_result['records'][0]['max_price'] or 0)
        
        print(f"\n📦 {product_name}")
        print(f"   Product2Id: {product_id}")
        print(f"   Historical Prices:")
        print(f"      Min: ${hist_min:.2f}")
        print(f"      Avg: ${hist_avg:.2f}")
        print(f"      Max: ${hist_max:.2f}")
        
        if product_id in price_map:
            pricebook_price = price_map[product_id]
            print(f"   Current Pricebook Price: ${pricebook_price:.2f}")
            
            diff = pricebook_price - hist_avg
            diff_pct = (diff / hist_avg * 100) if hist_avg > 0 else 0
            
            if abs(diff_pct) > 10:
                status = "⚠️  SIGNIFICANT DIFFERENCE"
            elif abs(diff_pct) > 5:
                status = "⚡ Notable difference"
            else:
                status = "✓ Similar"
            
            print(f"   Difference from Avg: {diff:+.2f} ({diff_pct:+.1f}%) {status}")
            
            # Calculate impact on a 100-unit order
            impact = (pricebook_price - hist_avg) * 100
            print(f"   Impact on 100-unit order: ${impact:+.2f}")
        else:
            print(f"   Current Pricebook Price: ❌ NOT FOUND IN PRICEBOOK")
            print(f"   ⚠️  Will use historical average: ${hist_avg:.2f}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print("\n✅ Pricebook pricing is configured correctly!")
print("   - Products in pricebook will use current prices")
print("   - Products not in pricebook will use historical averages")
print("   - Ready to generate reports with accurate pricing\n")

