#!/usr/bin/env python3
"""
Quantitative Sales Report App - Complete Solution
Single file that handles everything: dependencies, web interface, and report generation
"""

import os
import sys
import subprocess
import webbrowser
import threading
import time
import tempfile
import shutil
import socket
import signal
from pathlib import Path
from datetime import datetime
import json

# Flask imports
try:
    from flask import Flask, render_template_string, request, jsonify, redirect, url_for
    from flask_cors import CORS
except ImportError:
    print("Installing Flask dependencies...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'flask', 'flask-cors'], check=True)
    from flask import Flask, render_template_string, request, jsonify, redirect, url_for
    from flask_cors import CORS

# Import indicators_report
try:
    import indicators_report
except ImportError:
    print("Error: indicators_report.py not found in the same directory!")
    sys.exit(1)

# Import secure credentials manager
try:
    from b2b_insights_core.salesforce_client import SalesforceClient
except ImportError:
    print("Error: Salesforce client not found!")
    sys.exit(1)

app_dir = Path(__file__).parent
app = Flask(__name__, 
            static_folder=str(app_dir / 'static'),
            static_url_path='/static')
CORS(app)

# Global variables
current_analysis_result = None
sf_client = None
preloaded_user_data = None  # Store pre-loaded user data

def get_salesforce_connection():
    """Get or create Salesforce connection using secure credentials"""
    global sf_client
    if sf_client is None:
        sf_client = SalesforceClient()
    return sf_client.get_connection()

def get_user_initials_from_system():
    """Get user initials from Windows username if approved"""
    global sf_client
    try:
        if sf_client is None:
            sf_client = SalesforceClient()
        return sf_client.get_user_initials()
    except Exception:
        return None


# HTML Templates
MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantitative Sales - Q</title>
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="stylesheet" href="/static/css/landing.css">
    <style>
        /* Fallback styles in case CSS doesn't load */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            margin: 0;
            padding: 0;
        }
        .landing-container {
            max-width: 800px;
            width: 90%;
            text-align: center;
            padding: 40px;
        }
        .step.hidden {
            display: none;
        }
        .loading-message {
            font-size: 48px;
            font-weight: 400;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="landing-container">
        <!-- Step 2: Account selection (shown immediately if authorized) -->
        <div id="step2" class="step {% if not user_initials %}hidden{% endif %}">
            <div class="q-icon">
                <img src="/static/images/q-icon.svg" alt="Q">
            </div>
            <div class="greeting" id="welcomeMessage">Welcome, <span id="userInitials" style="font-style: italic;">{{ user_initials }}</span>!</div>
            <div class="question">Who needs our attention?</div>
            <div class="input-group">
                <div class="account-dropdown-wrapper">
                    <input 
                        type="text" 
                        class="account-search-input" 
                        id="accountSearchInput"
                        placeholder="Search accounts..."
                        autocomplete="off"
                    >
                    <div class="dropdown-arrow" id="dropdownArrow"></div>
                    <div class="account-dropdown" id="accountDropdown">
                        <!-- Account options will be populated here -->
                    </div>
                </div>
                <button class="next-button" id="nextButton2" onclick="goToStep3()">next</button>
            </div>
        </div>

        <!-- Step 3: Loading - generating report -->
        <div id="step3" class="step hidden">
            <div class="q-icon rotating">
                <img src="/static/images/q-icon.svg" alt="Q">
            </div>
            <div class="loading-message">Ok, I'll get on that report</div>
            <div class="loading-submessage">This'll take a few seconds...</div>
        </div>


        <!-- Step 5: Error state -->
        <div id="step5" class="step hidden">
            <div class="q-icon">
                <img src="/static/images/q-icon.svg" alt="Q">
            </div>
            <div class="error-message">Sorry about that, <span id="errorAccountName" style="font-style: italic;"></span></div>
            <div class="question">Who else needs our attention?</div>
            <div class="input-group">
                <button class="back-button" onclick="goBackFromError()">back</button>
            </div>
        </div>

        <!-- Step 6: Unauthorized user state (shown immediately if not authorized) -->
        <div id="step6" class="step {% if user_initials %}hidden{% endif %}">
            <div class="q-icon">
                <img src="/static/images/q-icon.svg" alt="Q">
            </div>
            <div class="error-message">Sorry, I don't recognise you</div>
        </div>
    </div>

    <script>
        // State management
        // Get user initials from template (passed from server at page load)
        let userInitials = '{{ user_initials }}';
        let selectedAccountId = '';
        let selectedAccountName = '';
        let userAccounts = {{ accounts_json|safe }};

        // Page is already rendered with correct state from server-side template
        // Debug helper function to log to terminal (defined early, before DOMContentLoaded)
        function debugLog(eventType, message, details = {}) {
            // Always log to console first (visible in browser console)
            const logMsg = `[DEBUG ${eventType}]: ${message}`;
            console.log(logMsg, details);
            
            // Also send to server for terminal logging (with error handling)
            const debugData = { event: eventType, message: message, details: details };
            
            // Use XMLHttpRequest as fallback if fetch fails
            try {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/debug', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onerror = function() {
                    console.error('XHR Debug log failed for:', eventType);
                };
                xhr.send(JSON.stringify(debugData));
            } catch (e) {
                console.error('Debug log XHR error:', e);
            }
            
            // Also try fetch as backup
            try {
                fetch('/api/debug', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(debugData)
                }).catch(err => {
                    console.error('Debug log fetch failed:', err);
                });
            } catch (e) {
                console.error('Debug log fetch error:', e);
            }
        }
        
        // Make debugLog available globally immediately
        window.debugLog = debugLog;
        
        // Test that debugLog works immediately
        console.log('=== SCRIPT LOADED ===');
        console.log('debugLog function defined:', typeof debugLog);
        console.log('window.debugLog defined:', typeof window.debugLog);
        
        // Immediate test call
        if (typeof debugLog === 'function') {
            debugLog('SCRIPT_LOAD', 'JavaScript script block executed');
        } else {
            console.error('ERROR: debugLog is not a function!');
        }
        
        // Just set up the page functionality when DOM is ready
        window.addEventListener('DOMContentLoaded', function() {
            console.log('DOMContentLoaded fired - calling debugLog');
            debugLog('PAGE_LOAD', 'DOMContentLoaded event fired');
            
            // Trim user initials
            userInitials = (userInitials || '').toString().trim();
            debugLog('PAGE_LOAD', 'Initial userInitials value', { userInitials: userInitials });
            
            if (userInitials && userInitials !== '' && userInitials !== '{{ user_initials }}') {
                // User is approved - show step2
                showStep2();
            } else {
                // User is NOT approved - show error screen
                showUnauthorizedError();
            }
        });
        

        function showUnauthorizedError() {
            // Ensure step6 is visible and step2 is hidden (should already be from template)
            const step2 = document.getElementById('step2');
            const step6 = document.getElementById('step6');
            
            if (step2) step2.classList.add('hidden');
            if (step6) {
                step6.classList.remove('hidden');
                step6.style.display = ''; // Ensure visible
            }
            
            // Wait 5 seconds then quit the application
            setTimeout(async () => {
                try {
                    // Send shutdown request to server
                    await fetch('/api/shutdown', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                } catch (error) {
                    // Silently handle shutdown request
                }
                
                // Try to close the window
                window.close();
                
                // If window.close() doesn't work (browser security), try alternative
                setTimeout(() => {
                    // Show message to manually close
                    document.querySelector('#step6 .error-message').textContent = 
                        'Sorry, I don\'t recognise you. Please close this window.';
                }, 100);
            }, 5000);
        }

        function showStep2() {
            if (!userInitials) {
                showUnauthorizedError();
                return;
            }
            
            // Ensure step2 is visible and step6 is hidden (should already be from template)
            const step2 = document.getElementById('step2');
            const step6 = document.getElementById('step6');
            
            if (step6) step6.classList.add('hidden');
            if (step2) {
                step2.classList.remove('hidden');
                step2.style.display = ''; // Ensure visible
            }
            
            // Set welcome message - always "Welcome" (never "Welcome back")
            const welcomeMessage = 'Welcome, <span style="font-style: italic;">' + userInitials + '</span>!';
            const welcomeElement = document.getElementById('welcomeMessage');
            if (welcomeElement) {
                welcomeElement.innerHTML = welcomeMessage;
            }
            
            // If accounts are already pre-loaded, use them; otherwise load them
            if (userAccounts && Array.isArray(userAccounts) && userAccounts.length > 0) {
                populateAccountDropdown(userAccounts);
            } else if (userAccounts && Array.isArray(userAccounts) && userAccounts.length === 0) {
                // Explicitly handle empty accounts array
                populateAccountDropdown([]);
            } else {
                // Load user's accounts (fallback if pre-loading didn't work)
                loadUserAccounts(userInitials);
            }
        }

        async function loadUserAccounts(initials) {
            try {
                const response = await fetch('/api/get_user_accounts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: initials })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Always populate dropdown, even if accounts array is empty
                    userAccounts = result.accounts || [];
                    populateAccountDropdown(userAccounts);
                } else {
                    // API call succeeded but returned error - show empty state
                    userAccounts = [];
                    populateAccountDropdown([]);
                }
            } catch (error) {
                // On error, still show the page with empty accounts
                userAccounts = [];
                populateAccountDropdown([]);
            }
        }

        function populateAccountDropdown(accounts) {
            const dropdown = document.getElementById('accountDropdown');
            dropdown.innerHTML = '';
            
            if (accounts.length === 0) {
                dropdown.innerHTML = '<div class="account-option" style="cursor: default; opacity: 0.6;">No accounts found</div>';
                return;
            }
            
            accounts.forEach(account => {
                const option = document.createElement('div');
                option.className = 'account-option';
                option.textContent = account.name;
                option.setAttribute('data-account-id', account.id);
                option.setAttribute('data-account-name', account.name);
                option.onclick = () => selectAccount(account.id, account.name);
                dropdown.appendChild(option);
            });
            
            // Set up search/filter functionality
            setupAccountSearch();
        }

        function setupAccountSearch() {
            const searchInput = document.getElementById('accountSearchInput');
            const dropdown = document.getElementById('accountDropdown');
            const dropdownArrow = document.getElementById('dropdownArrow');
            
            // Show dropdown when input is focused
            searchInput.addEventListener('focus', () => {
                dropdown.classList.add('show');
                dropdownArrow.classList.add('open');
                filterAccounts(searchInput.value);
            });
            
            // Filter accounts as user types
            searchInput.addEventListener('input', (e) => {
                const searchTerm = e.target.value;
                filterAccounts(searchTerm);
                dropdown.classList.add('show');
                dropdownArrow.classList.add('open');
                
                // Clear selection if user starts typing
                if (selectedAccountId && searchTerm !== selectedAccountName) {
                    selectedAccountId = '';
                    selectedAccountName = '';
                }
            });
            
            // Allow Enter to select first filtered result
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const visibleOptions = Array.from(dropdown.querySelectorAll('.account-option:not(.hidden)'));
                    if (visibleOptions.length > 0) {
                        const firstOption = visibleOptions[0];
                        const accountId = firstOption.getAttribute('data-account-id');
                        const accountName = firstOption.getAttribute('data-account-name');
                        if (accountId && accountName) {
                            selectAccount(accountId, accountName);
                        }
                    }
                }
            });
        }

        function filterAccounts(searchTerm) {
            const dropdown = document.getElementById('accountDropdown');
            const options = dropdown.querySelectorAll('.account-option');
            const term = searchTerm.toLowerCase();
            
            let visibleCount = 0;
            options.forEach(option => {
                const accountName = option.textContent.toLowerCase();
                if (accountName.includes(term)) {
                    option.classList.remove('hidden');
                    visibleCount++;
                } else {
                    option.classList.add('hidden');
                }
            });
            
            // Show "no results" if nothing matches
            if (visibleCount === 0 && searchTerm) {
                dropdown.innerHTML = '<div class="account-option" style="cursor: default; opacity: 0.6;">No matching accounts</div>';
            }
        }

        function selectAccount(accountId, accountName) {
            selectedAccountId = accountId;
            selectedAccountName = accountName;
            
            // Update input field
            const searchInput = document.getElementById('accountSearchInput');
            searchInput.value = accountName;
            
            // Close dropdown
            const dropdown = document.getElementById('accountDropdown');
            const dropdownArrow = document.getElementById('dropdownArrow');
            dropdown.classList.remove('show');
            dropdownArrow.classList.remove('open');
            
            // Account selected (button is always enabled)
        }

        function goToStep3() {
            if (!selectedAccountId) return;
            
            // Transition to loading state
            transitionTo('step2', 'step3', () => {
                // Start report generation
                generateReport(selectedAccountId);
            });
        }

        async function generateReport(accountId) {
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ account_id: accountId })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Redirect directly to results
                    window.location.href = '/results';
                } else {
                    // Show error state
                    showError(selectedAccountName);
                }
            } catch (error) {
                // Show error state
                showError(selectedAccountName);
            }
        }

        function showError(accountName) {
            // Set error account name
            document.getElementById('errorAccountName').textContent = accountName;
            
            // Transition to error state
            transitionTo('step3', 'step5');
        }

        function goBackFromError() {
            // Reset to step 2 with remembered initials
            selectedAccountId = '';
            selectedAccountName = '';
            
            const searchInput = document.getElementById('accountSearchInput');
            searchInput.value = '';
            
            // Transition back
            transitionTo('step5', 'step2', () => {
                // Update welcome message - always "Welcome" (never "Welcome back")
                const welcomeMsg = 'Welcome, <span style="font-style: italic;">' + userInitials + '</span>!';
                document.getElementById('welcomeMessage').innerHTML = welcomeMsg;
                
                // Reload accounts
                loadUserAccounts(userInitials);
            });
        }


        function transitionTo(fromStep, toStep, callback) {
            const from = document.getElementById(fromStep);
            const to = document.getElementById(toStep);
            
            from.classList.add('fade-out');
            
            setTimeout(() => {
                from.classList.add('hidden');
                from.classList.remove('fade-out');
                
                to.classList.remove('hidden');
                to.classList.add('fade-in');
                
                setTimeout(() => {
                    to.classList.remove('fade-in');
                    if (callback) callback();
                }, 500);
            }, 500);
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('accountDropdown');
            const searchInput = document.getElementById('accountSearchInput');
            const dropdownArrow = document.getElementById('dropdownArrow');
            
            if (dropdown && searchInput && 
                !searchInput.contains(e.target) && 
                !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
                if (dropdownArrow) {
                    dropdownArrow.classList.remove('open');
                }
            }
        });
    </script>
</body>
</html>
"""

RESULTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantitative Sales - Report Results</title>
    <style>
        body { 
            margin: 0; 
            padding: 0; 
            overflow: hidden;
        }
        .report-container {
            width: 100vw;
            height: 100vh;
            position: relative;
        }
        .full-screen { 
            width: 100%; 
            height: 100%; 
            border: none; 
        }
    </style>
</head>
<body>
    <div class="report-container">
        <iframe src="data:text/html;charset=utf-8,{{ html_report }}" class="full-screen" id="reportFrame"></iframe>
    </div>
    
    <script>
        // Listen for messages from the iframe
        window.addEventListener('message', function(event) {
            // Handle navigation requests from iframe
            if (event.data && event.data.action === 'navigate') {
                window.location.href = event.data.url;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main page with account selection"""
    # Use pre-loaded data if available, otherwise get it now
    global preloaded_user_data
    
    print("\n" + "="*70)
    print("PAGE LOAD: Getting user data for template")
    print("="*70)
    
    if preloaded_user_data:
        user_initials = preloaded_user_data.get('initials')
        user_accounts = preloaded_user_data.get('accounts', [])
        print(f"Using pre-loaded data: {user_initials}, {len(user_accounts)} accounts")
    else:
        # Fallback: get data now (shouldn't happen if pre-loading works)
        user_initials = get_user_initials_from_system()
        user_accounts = []
        print(f"Fallback: Getting user initials now: {user_initials}")
    
    if user_initials:
        print(f"✓ APPROVED USER: {user_initials} - Passing to template")
    else:
        print("✗ UNAUTHORIZED USER - Will show error screen")
    
    print("="*70)
    print(f"TEMPLATE RENDERING DEBUG:")
    print(f"  user_initials: {user_initials}")
    print(f"  step2 will be: {'visible' if user_initials else 'hidden'}")
    print("="*70)
    print("NOTE: If you don't see DEBUG messages after this, JavaScript may not be executing")
    print("Check browser console (F12) for JavaScript errors")
    print("="*70 + "\n")
    
    # Flush output immediately
    import sys
    sys.stdout.flush()
    
    # Convert accounts to JSON for template
    accounts_json = json.dumps(user_accounts) if user_accounts else '[]'
    
    return render_template_string(MAIN_TEMPLATE, 
                                user_initials=user_initials or '',
                                accounts_json=accounts_json,
                                account_id='',
                                account_name='',
                                generated_time='',
                                text_report='',
                                html_report='')

@app.route('/results')
def results():
    """Results page showing the generated reports"""
    global current_analysis_result
    
    if not current_analysis_result:
        return redirect(url_for('index'))
    
    # URL encode the HTML report for the iframe
    import urllib.parse
    encoded_html = urllib.parse.quote(current_analysis_result['html_report'])
    
    return render_template_string(RESULTS_TEMPLATE, html_report=encoded_html)

@app.route('/api/debug', methods=['POST', 'GET'])
def debug_log():
    """Debug endpoint to log client-side events to terminal"""
    try:
        # Handle GET requests (test endpoint)
        if request.method == 'GET':
            print(f"\n{'='*70}")
            print("DEBUG ENDPOINT TEST: GET request received")
            print(f"{'='*70}\n")
            return jsonify({'success': True, 'message': 'Debug endpoint is working'})
        
        # Handle POST requests
        data = request.get_json() or {}
        event_type = data.get('event', 'unknown')
        message = data.get('message', '')
        details = data.get('details', {})
        
        print(f"\n{'='*70}")
        print(f"DEBUG [{event_type}]: {message}")
        if details:
            for key, value in details.items():
                # Handle complex objects
                if isinstance(value, (dict, list)):
                    import json
                    print(f"  {key}: {json.dumps(value, indent=4, default=str)}")
                else:
                    print(f"  {key}: {value}")
        print(f"{'='*70}\n")
        
        # Flush output to ensure it appears immediately
        import sys
        sys.stdout.flush()
        
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        print(f"\n{'='*70}")
        print(f"DEBUG ERROR: {str(e)}")
        print(traceback.format_exc())
        print(f"{'='*70}\n")
        import sys
        sys.stdout.flush()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, images, fonts)"""
    from flask import send_from_directory
    try:
        return send_from_directory(app_dir / 'static', filename)
    except Exception as e:
        print(f"Warning: Could not serve static file {filename}: {e}")
        return '', 404

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    from flask import send_from_directory
    try:
        return send_from_directory(app_dir / 'static' / 'images', 'q-icon.ico', mimetype='image/x-icon')
    except:
        return '', 404

@app.route('/images/<filename>')
def serve_image(filename):
    """Serve product images from the images directory"""
    from flask import send_from_directory
    images_dir = app_dir / "images"
    return send_from_directory(images_dir, filename)

@app.route('/api/get_system_initials', methods=['GET'])
def get_system_initials():
    """Get user initials from Windows username if approved"""
    print("\n" + "="*70)
    print("API CALL: /api/get_system_initials")
    print("="*70)
    try:
        initials = get_user_initials_from_system()
        print(f"get_user_initials_from_system() returned: {initials}")
        
        if initials:
            response_data = {
                'success': True,
                'initials': initials,
                'source': 'system'
            }
            print(f"Returning SUCCESS: {response_data}")
            return jsonify(response_data)
        else:
            response_data = {
                'success': False,
                'initials': None,
                'message': 'User not found in approved list or could not detect username'
            }
            print(f"Returning FAILURE: {response_data}")
            return jsonify(response_data)
    except PermissionError as e:
        print(f"PermissionError: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'initials': None
        }), 403
    except Exception as e:
        print(f"Exception in get_system_initials: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'initials': None
        }), 500

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """Shutdown the Flask server (for unauthorized users)"""
    try:
        print("Shutting down application - unauthorized user detected")
        # Shutdown the Flask server
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            # Alternative shutdown method
            import os
            os._exit(0)
        func()
        return jsonify({'success': True, 'message': 'Server shutting down...'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_user_accounts', methods=['POST'])
def get_user_accounts():
    """Get accounts owned by a specific user"""
    print("\n" + "="*70)
    print("API CALL: /api/get_user_accounts")
    print("="*70)
    try:
        data = request.get_json()
        username_input = data.get('username', '').strip()
        print(f"Request received for username (original): {username_input}")
        
        if not username_input:
            print("ERROR: Username is empty")
            return jsonify({'error': 'Username is required', 'success': False}), 400
        
        # Set up Salesforce connection using secure credentials
        try:
            sf = get_salesforce_connection()
        except FileNotFoundError as e:
            return jsonify({
                'success': False,
                'error': 'Credentials not configured. Please run setup_credentials.py first.'
            }), 500
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to Salesforce: {str(e)}'
            }), 500
        
        # Step 1: Try to find the actual User record in Salesforce to get the exact username format
        # This handles case sensitivity issues
        actual_username = None
        username_variations = []
        
        # Generate username variations to try
        username_lower = username_input.lower()
        username_upper = username_input.upper()
        
        # Try both novozymes.com and novonesis.com domains
        domains = ['novozymes.com', 'novonesis.com']
        
        # Build list of username variations to try
        for domain in domains:
            if '@' not in username_input:
                username_variations.extend([
                    f"{username_lower}@{domain}",
                    f"{username_upper}@{domain}",
                    f"{username_input}@{domain}"  # Original case
                ])
            else:
                # Already has @, just add variations
                username_variations.extend([
                    username_lower,
                    username_upper,
                    username_input
                ])
        
        print(f"DEBUG: Trying to find User record with username variations:")
        for var in username_variations:
            print(f"  - {var}")
        
        # Query User object to find the exact username format
        for username_var in username_variations:
            try:
                user_query = f"""
                    SELECT Id, Username, Email, FirstName, LastName
                    FROM User
                    WHERE Username = '{username_var}'
                    LIMIT 1
                """
                print(f"DEBUG: Querying User object with: {username_var}")
                user_result = sf.query(user_query)
                
                if user_result['records']:
                    actual_username = user_result['records'][0]['Username']
                    print(f"SUCCESS: Found User record with Username: {actual_username}")
                    break
            except Exception as e:
                print(f"DEBUG: Query failed for {username_var}: {str(e)}")
                continue
        
        # If we found the actual username, use it. Otherwise, try pattern matching
        if actual_username:
            username_to_use = actual_username
            print(f"DEBUG: Using actual username from Salesforce: {username_to_use}")
        else:
            # Fallback: use the input username (case-insensitive search)
            username_to_use = username_input.lower() if '@' not in username_input else username_input.lower()
            print(f"DEBUG: User record not found, using input username (will try case-insensitive): {username_to_use}")
        
        all_results = []
        
        # Step 2: Query accounts using the actual username or variations
        if actual_username:
            # Use the exact username we found
            query = f"""
                SELECT Id, Name, Owner.Username
                FROM Account
                WHERE Owner.Username = '{actual_username}'
                AND (NOT Name LIKE '(%')
                ORDER BY Name ASC
            """
            print(f"DEBUG: Querying accounts with exact username: {actual_username}")
            result = sf.query_all(query)
            
            if len(result['records']) > 0:
                print(f"DEBUG: Found {len(result['records'])} parent/standalone accounts with exact match")
                all_results.extend(result['records'])
        else:
            # Try all username variations
            print(f"DEBUG: Trying username variations to find accounts...")
            for username_var in username_variations:
                try:
                    query = f"""
                        SELECT Id, Name, Owner.Username
                        FROM Account
                        WHERE Owner.Username = '{username_var}'
                        AND (NOT Name LIKE '(%')
                        ORDER BY Name ASC
                    """
                    print(f"DEBUG: Trying exact match: {username_var}")
                    result = sf.query_all(query)
                    
                    if len(result['records']) > 0:
                        print(f"DEBUG: Found {len(result['records'])} parent/standalone accounts with exact match")
                        all_results.extend(result['records'])
                        break  # Found results, stop trying variations
                except Exception as e:
                    print(f"DEBUG: Query failed for {username_var}: {str(e)}")
                    continue
        
        # If still no results, try case-insensitive LIKE query
        # Note: SOQL LIKE is case-insensitive by default
        if len(all_results) == 0:
            print(f"DEBUG: No exact match found, trying case-insensitive pattern match...")
            # Extract the username part (before @) for pattern matching
            username_part = username_input.split('@')[0] if '@' in username_input else username_input
            
            # Try LIKE query (SOQL LIKE is case-insensitive by default)
            # Try with both domains
            for domain in domains:
                try:
                    like_query = f"""
                        SELECT Id, Name, Owner.Username
                        FROM Account
                        WHERE Owner.Username LIKE '{username_part}@{domain}'
                        AND (NOT Name LIKE '(%')
                        ORDER BY Name ASC
                    """
                    print(f"DEBUG: Executing LIKE query for '{username_part}@{domain}'")
                    like_result = sf.query_all(like_query)
                    
                    if len(like_result['records']) > 0:
                        print(f"DEBUG: Found {len(like_result['records'])} parent/standalone accounts with pattern match")
                        all_results.extend(like_result['records'])
                        break  # Found results, stop trying
                except Exception as e:
                    print(f"DEBUG: LIKE query failed for {domain}: {str(e)}")
                    continue
            
            # If still no results, try without domain (match any domain)
            if len(all_results) == 0:
                try:
                    simple_like_query = f"""
                        SELECT Id, Name, Owner.Username
                        FROM Account
                        WHERE Owner.Username LIKE '{username_part}@%'
                        AND (NOT Name LIKE '(%')
                        ORDER BY Name ASC
                    """
                    print(f"DEBUG: Trying LIKE query without domain: '{username_part}@%'")
                    like_result = sf.query_all(simple_like_query)
                    print(f"DEBUG: Found {len(like_result['records'])} accounts with simple LIKE query")
                    all_results.extend(like_result['records'])
                except Exception as e2:
                    print(f"DEBUG: Simple LIKE query also failed: {str(e2)}")
        
        # Log what we found
        print(f"\n{'='*80}")
        print(f"ANALYZING RETURNED ACCOUNTS (showing first 10 for debugging)")
        print(f"{'='*80}")
        
        accounts = []
        seen_ids = set()  # Avoid duplicates
        child_prefix_count = 0
        
        # Sample the first 10 to debug
        for i, record in enumerate(all_results[:10]):
            account_name = record['Name']
            is_child = record.get('MBL_Is_Child_Account__c')
            parent_id = record.get('MBL_Custom_ParentAccountId_18__c')
            
            print(f"\n{i+1}. {account_name}")
            print(f"   ID: {record['Id']}")
            print(f"   Child Flag: {is_child}")
            print(f"   Parent ID: {parent_id}")
            
            if account_name.startswith('(FS)') or account_name.startswith('(EN)') or account_name.startswith('(DSS)') or account_name.startswith('(WS)') or account_name.startswith('(RH)'):
                print(f"   ⚠️  HAS CHILD PREFIX!")
        
        print(f"\n{'='*80}\n")
        
        # Now process all accounts and filter out child prefixes manually if needed
        for record in all_results:
            # Skip duplicates
            if record['Id'] in seen_ids:
                continue
            seen_ids.add(record['Id'])
            
            account_name = record['Name']
            parent_id = record.get('MBL_Custom_ParentAccountId_18__c')
            
            # MANUAL FILTER: Skip accounts with child prefixes if they have a parent ID OR if they look like children
            if account_name.startswith('(FS)') or account_name.startswith('(EN)') or account_name.startswith('(DSS)') or account_name.startswith('(WS)') or account_name.startswith('(RH)'):
                print(f"FILTERING OUT (child prefix): {account_name} (Parent ID: {parent_id})")
                child_prefix_count += 1
                continue
            
            # Clean up account name
            clean_name = account_name
            
            accounts.append({
                'id': record['Id'],
                'name': clean_name
            })
        
        print(f"\nDEBUG: Filtered out {child_prefix_count} accounts with child prefixes")
        print(f"DEBUG: Returning {len(accounts)} parent/standalone accounts")
        print(f"SUCCESS: Found {len(accounts)} accounts for user {username_input}")
        print("="*70 + "\n")
        
        # If no accounts found, provide helpful feedback
        if len(accounts) == 0:
            if actual_username:
                print(f"WARNING: User '{actual_username}' found in Salesforce but has no accounts")
                return jsonify({
                    'success': True,
                    'accounts': [],
                    'count': 0,
                    'message': f'User found but no accounts assigned. Username: {actual_username}'
                })
            else:
                print(f"WARNING: Could not find User record for '{username_input}' in Salesforce")
                return jsonify({
                    'success': True,
                    'accounts': [],
                    'count': 0,
                    'message': f'User not found in Salesforce. Please verify username: {username_input}'
                })
        
        return jsonify({
            'success': True,
            'accounts': accounts,
            'count': len(accounts)
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR getting user accounts: {str(e)}")
        print(f"ERROR details: {error_details}")
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}',
            'accounts': []
        }), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_account():
    """Run the indicators report analysis"""
    global current_analysis_result
    
    try:
        data = request.get_json()
        account_id = data.get('account_id')
        
        if not account_id:
            return jsonify({'error': 'account_id is required', 'success': False}), 400
        
        if len(account_id) != 18 or not account_id.startswith('001'):
            return jsonify({'error': 'Invalid account_id format', 'success': False}), 400
        
        # Set up Salesforce connection using secure credentials
        try:
            sf = get_salesforce_connection()
        except FileNotFoundError as e:
            return jsonify({
                'success': False,
                'error': 'Credentials not configured. Please run setup_credentials.py first.'
            }), 500
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to connect to Salesforce: {str(e)}'
            }), 500
        
        # Set the global sf variable in indicators_report module
        indicators_report.sf = sf
        
        # Get account info (name and owner)
        account_info = indicators_report.get_account_info(account_id)
        account_name = account_info['name']
        owner_username = account_info['owner_username']
        
        # Clean up account name - remove (DSS) prefix if present
        if account_name.startswith('(DSS) '):
            account_name = account_name[6:]  # Remove "(DSS) " prefix
        
        # Construct owner email
        owner_email = f"{owner_username}" if owner_username else "info@microbiomelabs.com"
        
        # Set up analysis parameters
        from datetime import datetime, timedelta
        end_date = datetime.now()
        analysis_start = end_date - timedelta(days=365 * 5)  # 5 years of data
        
        print(f"\n{'='*80}")
        print(f"RUNNING ANALYSIS FOR: {account_name} ({account_id})")
        print(f"{'='*80}\n")
        
        # Detailed debug for this account
        print(f"🔍 ACCOUNT RELATIONSHIP DEBUG:")
        try:
            debug_query = f"""
                SELECT Id, Name, Owner.Username, MBL_Is_Child_Account__c, MBL_Custom_ParentAccountId_18__c
                FROM Account
                WHERE Id = '{account_id}'
            """
            debug_result = sf.query_all(debug_query)
            if len(debug_result['records']) > 0:
                acc_record = debug_result['records'][0]
                print(f"   Account ID: {acc_record['Id']}")
                print(f"   Account Name: {acc_record['Name']}")
                print(f"   Owner: {acc_record.get('Owner', {}).get('Username', 'N/A') if acc_record.get('Owner') else 'N/A'}")
                print(f"   MBL_Is_Child_Account__c: {acc_record.get('MBL_Is_Child_Account__c')}")
                print(f"   MBL_Custom_ParentAccountId_18__c: {acc_record.get('MBL_Custom_ParentAccountId_18__c')}")
                
                # Check for child accounts
                child_query = f"""
                    SELECT Id, Name, MBL_Is_Child_Account__c
                    FROM Account
                    WHERE MBL_Custom_ParentAccountId_18__c = '{account_id}'
                """
                child_result = sf.query_all(child_query)
                print(f"\n   Child Accounts Found: {len(child_result['records'])}")
                if len(child_result['records']) > 0:
                    for child in child_result['records']:
                        print(f"      - {child['Name']}")
                        print(f"        ID: {child['Id']}")
                        print(f"        Child Flag: {child.get('MBL_Is_Child_Account__c')}")
                else:
                    print(f"      (No child accounts)")
                    
                # If this is a child account, show parent info
                parent_id = acc_record.get('MBL_Custom_ParentAccountId_18__c')
                if parent_id:
                    print(f"\n   ⚠️  THIS IS A CHILD ACCOUNT!")
                    parent_query = f"""
                        SELECT Id, Name
                        FROM Account
                        WHERE Id = '{parent_id}'
                    """
                    parent_result = sf.query_all(parent_query)
                    if len(parent_result['records']) > 0:
                        parent = parent_result['records'][0]
                        print(f"   Parent Account: {parent['Name']} ({parent['Id']})")
        except Exception as e:
            print(f"   Error getting account debug info: {e}")
        
        print(f"\n{'='*80}\n")
        
        # Get orders and distribute FS orders
        orders = indicators_report.get_account_orders(account_id, analysis_start, end_date)
        distributed_orders = indicators_report.distribute_monthly_orders(orders)
        
        # Create and run the combined analysis
        # Returns data in memory (no disk I/O) - eliminates path resolution issues in PyInstaller
        analysis_result = indicators_report.create_combined_analysis(
            account_id,
            analysis_start,
            end_date,
            resolution='3D',
            ma_window=90,
            warmup_days=90 * 2,
            orders=distributed_orders
        )
        
        # Extract data from memory (no file I/O needed)
        if not isinstance(analysis_result, dict):
            # Fallback: if function still returns just figure (backward compatibility)
            return jsonify({
                'success': False,
                'error': 'Analysis completed but data format is incorrect. Please check the logs.'
            }), 500
        
        fig = analysis_result.get('figure')
        html_content = analysis_result.get('html_content', '')
        text_report = analysis_result.get('text_report', '')
        result_account_name = analysis_result.get('account_name', account_name)
        
        if not text_report:
            return jsonify({
                'success': False,
                'error': 'Analysis completed but text report is empty'
            }), 500
        
        # Import sales dashboard functions
        from sales_dashboard import parse_sales_dashboard_data, create_sales_dashboard_html
        
        # Parse the text report for dashboard data (from memory, no file read)
        dashboard_data = parse_sales_dashboard_data(text_report)
        
        # Create the sales dashboard HTML
        # Get the current port for absolute URLs (needed for data URL iframe)
        current_port = request.environ.get('SERVER_PORT', '5000')
        base_url = f"http://localhost:{current_port}"
        
        sales_dashboard_html = create_sales_dashboard_html(
            account_name, 
            dashboard_data, 
            account_id, 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            base_url,
            owner_email
        )
        
        # Store results globally
        current_analysis_result = {
            'account_id': account_id,
            'account_name': account_name,
            'owner_email': owner_email,
            'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'html_report': sales_dashboard_html
        }
        
        return jsonify({
            'success': True,
            'account_id': account_id,
            'account_name': account_name,
            'owner_email': owner_email,
            'message': 'Analysis completed successfully'
        })
        
    except Exception as e:
        print(f"Error in analyze_account: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

def find_output_files(account_name):
    """Find the most recent generated output files for an account"""
    output_files = {}
    
    # Create safe filename from account name (same logic as indicators_report.py)
    safe_name = account_name.replace(' ', '_').replace(',', '').replace('.', '').replace('(', '').replace(')', '')
    
    # Look for opportunity report files with pattern: {safe_name}_opportunity_report_{date}.txt
    opportunity_pattern = f"{safe_name}_opportunity_report_*.txt"
    chart_pattern = f"{safe_name}_opportunity_chart_*.html"
    
    # Find all matching files
    opportunity_files = list(app_dir.glob(opportunity_pattern))
    chart_files = list(app_dir.glob(chart_pattern))
    
    # Sort files by date in filename (most recent first), then by modification time
    def sort_key(file_path):
        # Extract date from filename
        file_date = extract_date_from_filename(file_path.name)
        if file_date:
            # Use date from filename as primary sort key
            return (file_date, file_path.stat().st_mtime)
        else:
            # Fallback to modification time
            return (datetime.min.date(), file_path.stat().st_mtime)
    
    opportunity_files.sort(key=sort_key, reverse=True)
    chart_files.sort(key=sort_key, reverse=True)
    
    # Get the most recent files
    if opportunity_files:
        output_files['text'] = opportunity_files[0]
        file_date = extract_date_from_filename(opportunity_files[0].name)
        if file_date:
            print(f"Found opportunity report: {opportunity_files[0].name} (from {file_date})")
        else:
            print(f"Found opportunity report: {opportunity_files[0].name}")
    
    if chart_files:
        output_files['html'] = chart_files[0]
        file_date = extract_date_from_filename(chart_files[0].name)
        if file_date:
            print(f"Found chart file: {chart_files[0].name} (from {file_date})")
        else:
            print(f"Found chart file: {chart_files[0].name}")
    
    # If no files found with the exact pattern, try a broader search
    if not output_files:
        print(f"No files found with pattern {opportunity_pattern}, trying broader search...")
        
        # Look for any files containing the account name
        for file_path in app_dir.glob(f"*{safe_name}*"):
            if file_path.suffix == '.html':
                output_files['html'] = file_path
            elif file_path.suffix == '.txt':
                output_files['text'] = file_path
    
    return output_files

def extract_date_from_filename(filename):
    """Extract date from filename pattern: {name}_opportunity_report_{YYYYMMDD}.txt"""
    import re
    # Look for 8-digit date pattern (YYYYMMDD)
    date_match = re.search(r'(\d{8})', filename)
    if date_match:
        date_str = date_match.group(1)
        try:
            return datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            return None
    return None

def validate_file_recency(file_path, max_age_hours=24):
    """Validate that a file is recent enough to be used"""
    if not file_path or not file_path.exists():
        return False
    
    # First try to extract date from filename
    file_date = extract_date_from_filename(file_path.name)
    if file_date:
        current_date = datetime.now().date()
        days_old = (current_date - file_date).days
        is_recent = days_old <= (max_age_hours / 24)
        
        if not is_recent:
            print(f"Warning: File {file_path.name} is {days_old} days old (max allowed: {max_age_hours/24:.1f} days)")
        
        return is_recent
    
    # Fallback to file modification time
    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    current_time = datetime.now()
    age_hours = (current_time - file_time).total_seconds() / 3600
    
    is_recent = age_hours <= max_age_hours
    
    if not is_recent:
        print(f"Warning: File {file_path.name} is {age_hours:.1f} hours old (max allowed: {max_age_hours} hours)")
    
    return is_recent

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    try:
        if sys.platform == "win32":
            # Windows
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                subprocess.run(f'taskkill /PID {pid} /F', shell=True, check=True)
                                print(f"✓ Killed process {pid} using port {port}")
                            except subprocess.CalledProcessError:
                                pass
        else:
            # macOS/Linux
            result = subprocess.run(
                f'lsof -ti:{port}',
                shell=True, capture_output=True, text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"✓ Killed process {pid} using port {port}")
                    except (OSError, ValueError):
                        pass
    except Exception as e:
        print(f"Warning: Could not kill processes on port {port}: {e}")

def find_available_port(start_port=5000, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def setup_port(desired_port=5000):
    """Setup port by killing existing processes and finding available port"""
    print(f"Setting up port {desired_port}...")
    
    # Try to kill any existing processes on the desired port
    kill_process_on_port(desired_port)
    
    # Wait a moment for processes to die
    time.sleep(1)
    
    # Check if the desired port is now available
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', desired_port))
            print(f"✓ Port {desired_port} is available")
            return desired_port
    except OSError:
        print(f"Port {desired_port} still in use, finding alternative...")
        
        # Find an available port
        available_port = find_available_port(desired_port + 1)
        if available_port:
            print(f"✓ Using port {available_port} instead")
            return available_port
        else:
            print("✗ No available ports found")
            return None

def check_and_install_dependencies():
    """Check and install required dependencies"""
    print("Checking dependencies...")
    
    required_modules = [
        'pandas', 'pandas_ta', 'simple_salesforce', 
        'plotly', 'numpy', 'flask', 'flask_cors'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module.replace('-', '_'))
            print(f"✓ {module}")
        except ImportError:
            print(f"✗ {module} - missing")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"Installing missing dependencies: {', '.join(missing_modules)}")
        
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                         check=True, cwd=app_dir)
            print("✓ All dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies: {e}")
            return False
    
    return True

def preload_user_data():
    """Pre-load user authorization and accounts before opening browser"""
    global preloaded_user_data
    print("\n" + "="*70)
    print("PRE-LOADING: Checking authorization and loading accounts")
    print("="*70)
    
    try:
        # Get user initials
        user_initials = get_user_initials_from_system()
        
        if not user_initials:
            print("✗ UNAUTHORIZED USER - Will show error screen")
            preloaded_user_data = {
                'initials': None,
                'accounts': []
            }
            return
        
        print(f"✓ APPROVED USER: {user_initials}")
        
        # Pre-load accounts from Salesforce
        accounts = []
        try:
            sf = get_salesforce_connection()
            
            # Use the same logic as the API endpoint
            username_input = user_initials
            username_lower = username_input.lower()
            username_upper = username_input.upper()
            domains = ['novozymes.com', 'novonesis.com']
            
            # Try to find User record
            actual_username = None
            username_variations = []
            for domain in domains:
                if '@' not in username_input:
                    username_variations.extend([
                        f"{username_lower}@{domain}",
                        f"{username_upper}@{domain}",
                        f"{username_input}@{domain}"
                    ])
            
            # Query User object
            for username_var in username_variations:
                try:
                    user_query = f"""
                        SELECT Id, Username, Email, FirstName, LastName
                        FROM User
                        WHERE Username = '{username_var}'
                        LIMIT 1
                    """
                    user_result = sf.query(user_query)
                    if user_result['records']:
                        actual_username = user_result['records'][0]['Username']
                        print(f"✓ Found User record: {actual_username}")
                        break
                except:
                    continue
            
            # Query accounts
            if actual_username:
                query = f"""
                    SELECT Id, Name, Owner.Username
                    FROM Account
                    WHERE Owner.Username = '{actual_username}'
                    AND (NOT Name LIKE '(%')
                    ORDER BY Name ASC
                """
                result = sf.query_all(query)
                
                # Filter out child accounts
                for record in result['records']:
                    account_name = record['Name']
                    if not (account_name.startswith('(FS)') or account_name.startswith('(EN)') or 
                           account_name.startswith('(DSS)') or account_name.startswith('(WS)') or 
                           account_name.startswith('(RH)')):
                        accounts.append({
                            'id': record['Id'],
                            'name': account_name
                        })
            
            print(f"✓ Pre-loaded {len(accounts)} accounts")
        except Exception as e:
            print(f"⚠ Warning: Could not pre-load accounts: {str(e)}")
            print("   Accounts will be loaded when page opens")
            accounts = []
        
        preloaded_user_data = {
            'initials': user_initials,
            'accounts': accounts
        }
        
    except Exception as e:
        print(f"⚠ Error during pre-loading: {str(e)}")
        preloaded_user_data = {
            'initials': None,
            'accounts': []
        }
    
    print("="*70 + "\n")

def main():
    """Main function to start the application"""
    print("=" * 70)
    print("🚀 Quantitative Sales - Report Generator")
    print("=" * 70)
    
    # Check dependencies
    if not check_and_install_dependencies():
        input("Press Enter to exit...")
        return
    
    # Check if indicators_report.py exists
    if not (app_dir / "indicators_report.py").exists():
        print("✗ indicators_report.py not found!")
        print("Please ensure the indicators_report.py file is in the same directory")
        input("Press Enter to exit...")
        return
    
    print("✓ All requirements met")
    
    # PRE-LOAD user data BEFORE starting server
    preload_user_data()
    
    # Setup port (kill existing processes and find available port)
    port = setup_port(5000)
    if not port:
        print("✗ Could not find an available port")
        input("Press Enter to exit...")
        return
    
    print(f"\nStarting web server on port {port}...")
    print("The application will open in your browser automatically")
    print("Press Ctrl+C to stop the server")
    print("=" * 70)
    
    # Open browser after server is ready (longer delay to ensure server is up)
    def open_browser():
        time.sleep(3)  # Increased delay to ensure server is ready
        webbrowser.open(f"http://localhost:{port}")
    
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Start Flask app
    # Use 127.0.0.1 (localhost) instead of 0.0.0.0 to avoid Windows Firewall prompts
    # This only listens on localhost, not external network interfaces
    try:
        app.run(debug=False, host='127.0.0.1', port=port, use_reloader=False)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")

if __name__ == "__main__":
    main()
