
1. app.py (Flask Backend)
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import random

app = Flask(__name__)
app.secret_key = 'your_super_secret_key' # IMPORTANT: Change this in production!

DATABASE = 'game_data.db'

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1_id INTEGER NOT NULL,
                player2_id INTEGER, -- Null for AI or waiting for opponent
                current_turn_player_id INTEGER,
                game_state TEXT NOT NULL, -- JSON string of game state
                FOREIGN KEY (player1_id) REFERENCES users(id),
                FOREIGN KEY (player2_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

# Call this once when the app starts
init_db()

# --- Game Logic (Simplified) ---
creature_stats = {
    "fire": {"hp": 100, "attack": 20, "weakness": "water", "strength": "earth"},
    "water": {"hp": 100, "attack": 20, "weakness": "earth", "strength": "fire"},
    "earth": {"hp": 100, "attack": 20, "weakness": "fire", "strength": "water"},
    "air": {"hp": 100, "attack": 20, "weakness": "none", "strength": "none"} # Air is balanced
}

def create_initial_game_state(player_creature_type):
    # For simplicity, player 2 will always be a random AI for now
    ai_creature_type = random.choice(list(creature_stats.keys()))
    while ai_creature_type == player_creature_type: # Ensure different types
        ai_creature_type = random.choice(list(creature_stats.keys()))

    return {
        "player_creature": {
            "type": player_creature_type,
            "hp": creature_stats[player_creature_type]["hp"]
        },
        "ai_creature": {
            "type": ai_creature_type,
            "hp": creature_stats[ai_creature_type]["hp"]
        },
        "log": [],
        "game_over": False,
        "winner": None
    }

def apply_damage(attacker_type, defender_type, base_damage):
    damage = base_damage
    if creature_stats[attacker_type]["strength"] == defender_type:
        damage *= 1.5 # 50% extra damage
    elif creature_stats[attacker_type]["weakness"] == defender_type:
        damage *= 0.5 # 50% less damage
    return int(damage) # Ensure integer damage

def process_player_turn(current_game_state):
    player_creature = current_game_state["player_creature"]
    ai_creature = current_game_state["ai_creature"]
    log = current_game_state["log"]

    # Player attacks AI
    damage_to_ai = apply_damage(
        player_creature["type"],
        ai_creature["type"],
        creature_stats[player_creature["type"]]["attack"]
    )
    ai_creature["hp"] -= damage_to_ai
    log.append(f"Your {player_creature['type'].capitalize()} attacks! AI's {ai_creature['type'].capitalize()} takes {damage_to_ai} damage.")

    if ai_creature["hp"] <= 0:
        current_game_state["game_over"] = True
        current_game_state["winner"] = "player"
        log.append(f"AI's {ai_creature['type'].capitalize()} has been defeated! You win!")
        return current_game_state

    return current_game_state

def process_ai_turn(current_game_state):
    player_creature = current_game_state["player_creature"]
    ai_creature = current_game_state["ai_creature"]
    log = current_game_state["log"]

    # AI attacks Player
    damage_to_player = apply_damage(
        ai_creature["type"],
        player_creature["type"],
        creature_stats[ai_creature["type"]]["attack"]
    )
    player_creature["hp"] -= damage_to_player
    log.append(f"AI's {ai_creature['type'].capitalize()} attacks! Your {player_creature['type'].capitalize()} takes {damage_to_player} damage.")

    if player_creature["hp"] <= 0:
        current_game_state["game_over"] = True
        current_game_state["winner"] = "ai"
        log.append(f"Your {player_creature['type'].capitalize()} has been defeated! You lose!")
        return current_game_state

    return current_game_state

# --- Routes ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and user[2] == password: # In real app, hash passwords!
                session['user_id'] = user[0]
                session['username'] = user[1]
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                return redirect(url_for('login', message='Registration successful! Please log in.'))
            except sqlite3.IntegrityError:
                return render_template('register.html', error='Username already exists.')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/start_game', methods=['POST'])
def start_game():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    player_id = session['user_id']
    creature_type = request.json.get('creature_type')

    if creature_type not in creature_stats:
        return jsonify({"error": "Invalid creature type"}), 400

    # End any existing games for this user (for simplicity)
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM game_sessions WHERE player1_id = ?", (player_id,))
        conn.commit()

    initial_state = create_initial_game_state(creature_type)
    game_state_json = json.dumps(initial_state)

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO game_sessions (player1_id, current_turn_player_id, game_state) VALUES (?, ?, ?)",
            (player_id, player_id, game_state_json) # Player 1 always starts
        )
        conn.commit()
        game_id = cursor.lastrowid
    
    return jsonify({"success": True, "game_id": game_id, "game_state": initial_state})

@app.route('/get_game_state/<int:game_id>')
def get_game_state(game_id):
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    player_id = session['user_id']
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT game_state, current_turn_player_id FROM game_sessions WHERE id = ? AND player1_id = ?",
            (game_id, player_id)
        )
        game_session_data = cursor.fetchone()

        if not game_session_data:
            return jsonify({"error": "Game not found or not authorized"}), 404

        game_state = json.loads(game_session_data[0])
        current_turn_player_id = game_session_data[1]

        # Determine whose turn it is for the frontend
        game_state["your_turn"] = (current_turn_player_id == player_id)

        return jsonify({"success": True, "game_state": game_state})

@app.route('/perform_action/<int:game_id>', methods=['POST'])
def perform_action(game_id):
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    player_id = session['user_id']
    
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT game_state, current_turn_player_id FROM game_sessions WHERE id = ? AND player1_id = ?",
            (game_id, player_id)
        )
        game_session_data = cursor.fetchone()

        if not game_session_data:
            return jsonify({"error": "Game not found or not authorized"}), 404

        game_state = json.loads(game_session_data[0])
        current_turn_player_id = game_session_data[1]

        if game_state["game_over"]:
            return jsonify({"error": "Game is already over"}), 400

        if current_turn_player_id != player_id:
            return jsonify({"error": "It's not your turn"}), 400

        # Process player's turn
        game_state = process_player_turn(game_state)

        if not game_state["game_over"]:
            # Process AI's turn immediately if not game over
            game_state = process_ai_turn(game_state)
            if not game_state["game_over"]:
                # If game not over, next turn is player's again (simple turn structure)
                next_turn_player_id = player_id
            else:
                next_turn_player_id = None # Game over, no next turn
        else:
            next_turn_player_id = None # Game over, no next turn

        updated_game_state_json = json.dumps(game_state)
        cursor.execute(
            "UPDATE game_sessions SET game_state = ?, current_turn_player_id = ? WHERE id = ?",
            (updated_game_state_json, next_turn_player_id, game_id)
        )
        conn.commit()

        # Add "your_turn" status to the response for frontend
        game_state["your_turn"] = (next_turn_player_id == player_id) # Should be True if game isn't over

        return jsonify({"success": True, "game_state": game_state})

if __name__ == '__main__':
    app.run(debug=True)


        
