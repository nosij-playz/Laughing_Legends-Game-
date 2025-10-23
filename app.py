from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import json
import sqlite3
import os
from functools import wraps
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Initialize Firebase
try:
    # Get Firebase credentials path from environment variable
    firebase_cred_path = os.environ.get('FIREBASE_CREDENTIALS')
    
    # Check if file exists before initializing
    if os.path.exists(firebase_cred_path):
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print(f"✅ Firebase initialized successfully with: {firebase_cred_path}")
    else:
        print(f"⚠️ Firebase credentials file not found at: {firebase_cred_path}")
        print("🚫 Using mock data mode")
        db = None
except Exception as e:
    print(f"❌ Firebase initialization failed: {e}")
    print("🚫 Using mock data mode")
    db = None

# Initialize SQLite
def init_sqlite():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS game_progress
                 (team_name TEXT, current_image INTEGER, completed_images TEXT, 
                  current_score INTEGER, hints_used INTEGER)''')
    conn.commit()
    conn.close()

init_sqlite()

# Load game data and count images
with open("data.json", "r", encoding="utf-8") as f:
    game_data = json.load(f)

# Get available image numbers from actual data.json keys
def get_available_images():
    """Get list of image numbers that actually exist in game_data"""
    available_images = []
    for key in game_data.keys():
        if key.startswith('LAUGH/'):
            try:
                # Extract number from "LAUGH/050.jpg"
                number_str = key.split('/')[1].split('.')[0]
                number = int(number_str)
                available_images.append(number)
            except (ValueError, IndexError):
                continue
    return sorted(available_images)

# Get available images
AVAILABLE_IMAGES = get_available_images()
TOTAL_AVAILABLE_IMAGES = len(AVAILABLE_IMAGES)
print(f"🎯 Total images in data.json: {len(game_data.keys())}")
print(f"📊 Available image numbers: {TOTAL_AVAILABLE_IMAGES}")
print(f"🔢 Image range: {min(AVAILABLE_IMAGES) if AVAILABLE_IMAGES else 0} - {max(AVAILABLE_IMAGES) if AVAILABLE_IMAGES else 0}")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'team_name' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'team_name' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        unique_code = request.form.get('unique_code')
        
        # Verify code with Firestore (if Firebase is available)
        if db is not None:
            try:
                participants_ref = db.collection('participants')
                query = participants_ref.where('uniqueCode', '==', unique_code).limit(1)
                results = query.get()
                
                if len(results) == 1:
                    team_data = results[0].to_dict()
                    session['team_name'] = team_data['teamName']
                    session['unique_code'] = unique_code
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('login.html', error='Invalid code!')
                    
            except Exception as e:
                print(f"Firebase error: {e}")
                return render_template('login.html', error='Database error!')
        else:
            # Mock login for development without Firebase
            session['team_name'] = f"Team-{unique_code}"
            session['unique_code'] = unique_code
            return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    team_name = session['team_name']
    
    # Get leaderboard data from Firestore (if available)
    if db is not None:
        try:
            leaderboard_ref = db.collection('leaderboard')
            query = leaderboard_ref.where('name', '==', team_name).limit(1)
            results = query.get()
            
            if len(results) == 1:
                team_stats = results[0].to_dict()
                status = team_stats.get('status', 'offline')
                score = team_stats.get('totalPoints', 0)
                wins = team_stats.get('wins', 0)
                games_played = team_stats.get('gamesPlayed', 0)
            else:
                status, score, wins, games_played = 'offline', 0, 0, 0
        except Exception as e:
            print(f"Firestore error: {e}")
            status, score, wins, games_played = 'offline', 0, 0, 0
    else:
        # Mock data for development
        status, score, wins, games_played = 'online', 150, 5, 10
    
    return render_template('dashboard.html', 
                         team_name=team_name,
                         status=status,
                         score=score,
                         wins=wins,
                         games_played=games_played,
                         total_images=TOTAL_AVAILABLE_IMAGES)

@app.route('/api/status')
@login_required
def api_status():
    team_name = session['team_name']
    
    if db is not None:
        try:
            leaderboard_ref = db.collection('leaderboard')
            query = leaderboard_ref.where('name', '==', team_name).limit(1)
            results = query.get()
            
            if len(results) == 1:
                team_data = results[0].to_dict()
                return jsonify({
                    'status': team_data.get('status', 'offline'),
                    'score': team_data.get('totalPoints', 0),
                    'wins': team_data.get('wins', 0),
                    'games_played': team_data.get('gamesPlayed', 0)
                })
        except Exception as e:
            print(f"Firestore error: {e}")
    
    # Return mock data if Firebase is not available
    return jsonify({'status': 'online', 'score': 150, 'wins': 5, 'games_played': 10})

@app.route('/image-select')
@login_required
def image_select():
    # Only select from images that actually exist in game_data
    if AVAILABLE_IMAGES:
        # Select 4 unique random images from available ones
        random_images = random.sample(AVAILABLE_IMAGES, min(4, len(AVAILABLE_IMAGES)))
    else:
        random_images = []
        print("❌ No available images found in game_data!")
    
    print(f"🎲 Selected images: {random_images}")
    print(f"📊 Total available images: {TOTAL_AVAILABLE_IMAGES}")
    
    return render_template('image_select.html', 
                         random_images=random_images,
                         total_images=TOTAL_AVAILABLE_IMAGES)

def extract_questions_from_data(image_data):
    """Extract all questions from any data structure"""
    questions = []
    
    print(f"🔍 Data type: {type(image_data)}")
    
    if isinstance(image_data, dict):
        print("📊 Processing as dictionary...")
        for key, value in image_data.items():
            print(f"   Key: {key}, Type: {type(value)}")
            
            # Get points for this difficulty level
            points = get_difficulty_score(key)
            
            if isinstance(value, list):
                # Structure: {"easy": [questions], "medium": [questions], "impossible": [questions]}
                for item in value:
                    if isinstance(item, dict) and 'question' in item:
                        questions.append({
                            'question': item['question'],
                            'answer': item.get('answer', ''),
                            'hints': item.get('hints', []),
                            'difficulty': key,
                            'points': points
                        })
            elif isinstance(value, dict) and 'question' in value:
                # Structure: {"easy": {"question": "...", ...}}
                questions.append({
                    'question': value['question'],
                    'answer': value.get('answer', ''),
                    'hints': value.get('hints', []),
                    'difficulty': key,
                    'points': points
                })
    
    elif isinstance(image_data, list):
        print("📊 Processing as list...")
        for item in image_data:
            if isinstance(item, dict) and 'question' in item:
                questions.append({
                    'question': item['question'],
                    'answer': item.get('answer', ''),
                    'hints': item.get('hints', []),
                    'difficulty': item.get('difficulty', 'easy')
                })
    
    print(f"📝 Extracted {len(questions)} questions")
    return questions

def get_difficulty_score(difficulty):
    """Get score points based on difficulty level"""
    difficulty_scores = {
        'easy': 10,
        'medium': 20,
        'hard': 30,
        'impossible': 50
    }
    return difficulty_scores.get(difficulty, 10)

@app.route('/game/<int:image_number>')
@login_required
def game(image_number):
    print(f"\n🎮 === GAME ROUTE CALLED ===")
    print(f"📥 Requested image number: {image_number}")
    
    # Find the image data
    image_key = f"LAUGH/{image_number:03d}.jpg"
    
    if image_key in game_data:
        image_data = game_data[image_key]
        print(f"✅ Found image: '{image_key}'")
        
        # Extract all questions
        all_questions = extract_questions_from_data(image_data)
        
        if not all_questions:
            print("❌ No questions found in the data!")
            print("💡 Data content:", image_data)
            return redirect(url_for('image_select'))
        
        # Select 10 random questions (or all if less than 10)
        selected_count = min(10, len(all_questions))
        selected_questions = random.sample(all_questions, selected_count)
        
        print(f"🎲 Selected {selected_count} random questions from {len(all_questions)} available")
        
        # Group by difficulty for the template
        questions_by_difficulty = {}
        for question in selected_questions:
            difficulty = question['difficulty']
            if difficulty not in questions_by_difficulty:
                questions_by_difficulty[difficulty] = []
            
            question_data = {
                'question': question['question'],
                'answer': question['answer'],
                    'hints': question['hints'],
                    'points': question['points']
            }
            questions_by_difficulty[difficulty].append(question_data)
        
        print(f"📊 Difficulties found: {list(questions_by_difficulty.keys())}")
        print(f"🎯 Rendering game.html with {selected_count} questions")
        print("=== GAME ROUTE END ===\n")
        
        # Create the URL for the image using url_for
        image_url = url_for('static', filename=image_key)
        
        return render_template('game.html', 
                             image_number=image_number,
                             image_key=image_key,
                             image_url=image_url,
                             image_data=questions_by_difficulty,
                             total_questions=selected_count)
    else:
        print(f"❌ Image '{image_key}' not found in game_data!")
        print(f"📊 Available images: {TOTAL_AVAILABLE_IMAGES}")
        print(f"🔢 Available numbers: {AVAILABLE_IMAGES}")
        
        # Show error message on image select page
        return redirect(url_for('image_select'))

@app.route('/api/update_score', methods=['POST'])
@login_required
def update_score():
    data = request.json
    points = data.get('points', 0)
    team_name = session['team_name']
    
    print(f"Updating score for {team_name}: +{points} points")
    
    # Update Firestore score (if Firebase is available)
    if db is not None:
        try:
            leaderboard_ref = db.collection('leaderboard')
            query = leaderboard_ref.where('name', '==', team_name).limit(1)
            results = query.get()
            
            if len(results) == 1:
                doc = results[0]
                current_data = doc.to_dict()
                
                update_data = {}
                
                # Update totalPoints if it exists
                if 'totalPoints' in current_data:
                    current_score = current_data.get('totalPoints', 0)
                    new_score = current_score + points
                    update_data['totalPoints'] = new_score
                    print(f"✅ totalPoints updated: {current_score} -> {new_score}")
                else:
                    print("❌ totalPoints field not found in document")
                    return jsonify({'success': False, 'error': 'totalPoints field not found'})
                
                # Update wins (questions completed) if it exists
                if 'wins' in current_data:
                    current_wins = current_data.get('wins', 0)
                    new_wins = current_wins + 1
                    update_data['wins'] = new_wins
                    print(f"✅ wins (questions) updated: {current_wins} -> {new_wins}")
                
                # Update status to online when active
                if 'status' in current_data:
                    update_data['status'] = 'online'
                    print("✅ Status updated to: online")
                
                if update_data:
                    doc.reference.update(update_data)
                    print(f"✅ Firestore updated successfully: {update_data}")
                    return jsonify({'success': True, 'updated_fields': update_data})
                else:
                    print("❌ No fields to update")
                    return jsonify({'success': False, 'error': 'No matching fields to update'})
                    
            else:
                print("❌ Team not found in leaderboard")
                return jsonify({'success': False, 'error': 'Team not found'})
                
        except Exception as e:
            print(f"❌ Score update error: {e}")
            return jsonify({'success': False, 'error': str(e)})
    else:
        # Mock success response when Firebase is not available
        print(f"✅ Mock score update: {team_name} +{points} points")
        return jsonify({'success': True, 'mock_update': True, 'points_added': points})

@app.route('/debug-images')
def debug_images():
    """Check all available image keys in data.json"""
    available_keys = list(game_data.keys())
    available_numbers = get_available_images()
    
    return jsonify({
        'total_images_in_json': len(available_keys),
        'available_image_numbers': available_numbers,
        'total_available_images': len(available_numbers),
        'missing_numbers': find_missing_numbers(available_numbers),
        'sample_keys': available_keys[:10]  # First 10 keys
    })

def find_missing_numbers(available_numbers):
    """Find gaps in the image numbering"""
    if not available_numbers:
        return []
    
    min_num = min(available_numbers)
    max_num = max(available_numbers)
    all_numbers = set(range(min_num, max_num + 1))
    available_set = set(available_numbers)
    return sorted(all_numbers - available_set)

@app.route('/api/complete_image', methods=['POST'])
@login_required
def complete_image():
    """Update gamesPlayed when an image is completed"""
    team_name = session['team_name']
    
    print(f"Marking image completion for {team_name}")
    
    if db is not None:
        try:
            leaderboard_ref = db.collection('leaderboard')
            query = leaderboard_ref.where('name', '==', team_name).limit(1)
            results = query.get()
            
            if len(results) == 1:
                doc = results[0]
                current_data = doc.to_dict()
                
                update_data = {}
                
                # Update gamesPlayed if it exists
                if 'gamesPlayed' in current_data:
                    current_games = current_data.get('gamesPlayed', 0)
                    new_games = current_games + 1
                    update_data['gamesPlayed'] = new_games
                    print(f"✅ gamesPlayed updated: {current_games} -> {new_games}")
                else:
                    print("⚠️ gamesPlayed field not found in document")
                
                # Update status to online
                if 'status' in current_data:
                    update_data['status'] = 'online'
                    print("✅ Status updated to: online")
                
                if update_data:
                    doc.reference.update(update_data)
                    print(f"✅ Image completion recorded: {update_data}")
                    return jsonify({'success': True, 'updated_fields': update_data})
                else:
                    return jsonify({'success': False, 'error': 'No fields to update'})
                    
            else:
                return jsonify({'success': False, 'error': 'Team not found'})
                
        except Exception as e:
            print(f"❌ Image completion update error: {e}")
            return jsonify({'success': False, 'error': str(e)})
    else:
        # Mock success response when Firebase is not available
        print(f"✅ Mock image completion: {team_name}")
        return jsonify({'success': True, 'mock_update': True})

@app.route('/debug-difficulties')
def debug_difficulties():
    """Debug route to see all difficulty levels in data"""
    print("🔍 DEBUG: Checking all difficulty levels")
    
    all_difficulties = set()
    for image_key, image_data in game_data.items():
        if isinstance(image_data, dict):
            all_difficulties.update(image_data.keys())
    
    print(f"📊 All difficulty levels found: {sorted(all_difficulties)}")
    return f"All difficulty levels: {sorted(all_difficulties)}"

@app.route('/debug-leaderboard')
@login_required
def debug_leaderboard():
    """Debug route to check leaderboard data for current team"""
    team_name = session['team_name']
    
    if db is not None:
        try:
            leaderboard_ref = db.collection('leaderboard')
            query = leaderboard_ref.where('name', '==', team_name).limit(1)
            results = query.get()
            
            if len(results) == 1:
                team_data = results[0].to_dict()
                return jsonify({
                    'team_name': team_name,
                    'current_data': team_data,
                    'available_fields': list(team_data.keys())
                })
            else:
                return jsonify({'error': 'Team not found'})
        except Exception as e:
            return jsonify({'error': str(e)})
    else:
        return jsonify({'error': 'Firebase not available', 'team_name': team_name})

@app.route('/check-image/<int:image_number>')
def check_image(image_number):
    """Check if specific image exists"""
    image_key = f"LAUGH/{image_number:03d}.jpg"
    exists = image_key in game_data
    
    return jsonify({
        'image_number': image_number,
        'image_key': image_key,
        'exists': exists,
        'available_images_count': TOTAL_AVAILABLE_IMAGES
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)