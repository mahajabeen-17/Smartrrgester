static/script.js (Frontend JavaScript)
document.addEventListener('DOMContentLoaded', () => {
    const startGameBtn = document.getElementById('start-game-btn');
    const creatureSelect = document.getElementById('creature-select');
    const gameSetupDiv = document.getElementById('game-setup');
    const gameAreaDiv = document.getElementById('game-area');
    const playerTypeSpan = document.getElementById('player-type');
    const playerHpSpan = document.getElementById('player-hp');
    const aiTypeSpan = document.getElementById('ai-type');
    const aiHpSpan = document.getElementById('ai-hp');
    const gameLogList = document.getElementById('log-list');
    const attackBtn = document.getElementById('attack-btn');
    const turnIndicator = document.getElementById('turn-indicator');
    const gameStatus = document.getElementById('game-status');
    const restartGameBtn = document.getElementById('restart-game-btn');

    let currentGameId = null;

    function updateGameUI(gameState) {
        playerTypeSpan.textContent = gameState.player_creature.type.capitalize();
        playerHpSpan.textContent = Math.max(0, gameState.player_creature.hp); // Don't show negative HP
        aiTypeSpan.textContent = gameState.ai_creature.type.capitalize();
        aiHpSpan.textContent = Math.max(0, gameState.ai_creature.hp);

        gameLogList.innerHTML = ''; // Clear previous log
        gameState.log.forEach(entry => {
            const li = document.createElement('li');
            li.textContent = entry;
            gameLogList.appendChild(li);
        });
        gameLogList.scrollTop = gameLogList.scrollHeight; // Auto-scroll to bottom

        if (gameState.game_over) {
            attackBtn.style.display = 'none';
            turnIndicator.style.display = 'none';
            gameStatus.textContent = `Game Over! Winner: ${gameState.winner.capitalize()}`;
            restartGameBtn.style.display = 'block';
        } else {
            attackBtn.style.display = 'block';
            restartGameBtn.style.display = 'none';
            gameStatus.textContent = '';
            if (gameState.your_turn) {
                turnIndicator.textContent = "It's your turn!";
                attackBtn.disabled = false;
            } else {
                turnIndicator.textContent = "Waiting for AI's turn..."; // In this simplified example, AI takes its turn immediately
                attackBtn.disabled = true;
            }
        }
    }

    function fetchGameState() {
        if (!currentGameId) return;

        fetch(`/get_game_state/${currentGameId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateGameUI(data.game_state);
