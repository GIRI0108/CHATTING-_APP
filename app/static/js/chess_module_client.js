// static/js/chess_module_client.js

let chessGame = null;
let chessBoard = null;
let myTurn = true;

// Called by chess.html through init_private_module_chess()
function init_chess_module() {
    console.log("Chess module initialized");

    const container = document.getElementById("chessBoardContainer");
    container.innerHTML = `
        <div id="gameBoard" style="width: 400px"></div>
    `;

    // Create a new game
    chessGame = new Chess();

    // Render the board
    chessBoard = Chessboard("gameBoard", {
        draggable: true,
        position: "start",
        onDrop: onMove
    });

    // Start game button
    document.getElementById("chessStartBtn").onclick = () => {
        resetChessGame();
        socket.emit("private:module:start", {conv_id, module:"chess"});
    };

    // Listen for remote moves
    window.addEventListener("game:update", updateFromRemote);
}

// Local move
function onMove(source, target) {
    if (!myTurn) return "snapback";

    let move = chessGame.move({from: source, to: target});
    if (!move) return "snapback";

    myTurn = false;

    socket.emit("game:move", {
        conv_id,
        game: "chess",
        state: chessGame.fen()
    });
}

// Update from opponent
function updateFromRemote(e) {
    const d = e.detail;
    if (d.game !== "chess") return;

    chessGame.load(d.state);
    chessBoard.position(chessGame.fen());
    myTurn = true;
}

// Reset
function resetChessGame() {
    chessGame = new Chess();
    chessBoard.position("start");
    myTurn = true;
}
