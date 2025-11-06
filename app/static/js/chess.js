let chessSocket = io();
let chessGame = null;
let chessBoard = null;
let chessMyTurn = true;

function startGame(gameType) {
    if (gameType !== "chess") return;

    fetch(`/start/chess/${conv_id}`, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            initChess();
        });
}

function initChess() {
    chessGame = new Chess();
    chessBoard = Chessboard('gameBoard', {
        draggable: true,
        position: 'start',
        onDrop: onChessMove
    });
}

function onChessMove(source, target) {
    if (!chessMyTurn) return "snapback";

    let move = chessGame.move({ from: source, to: target });

    if (!move) return "snapback";

    chessMyTurn = false;

    chessSocket.emit("game:move", {
        conv_id,
        game: "chess",
        state: chessGame.fen()
    });
}

chessSocket.on("game:update", (data) => {
    if (data.game !== "chess") return;

    chessGame.load(data.state);
    chessBoard.position(chessGame.fen());
    chessMyTurn = true;
});

// Ensure a canonical init function is available for private_room loader
function init_chess(){
  // If your chess code already has an init, call it or wire events here
  console.log("init_chess called");

  // Example: if you have a function `renderChessBoard()` call it
  if (typeof renderChessBoard === "function") renderChessBoard();

  // When the player makes a move, emit game:move
  // Replace this with your move callback
  window.addEventListener("chess:localmove", (e)=>{
    const state = e.detail; // e.g. {from:'e2', to:'e4', fen: '...' }
    socket.emit("game:move", {conv_id, game:"chess", state});
  });

  // Listen to remote updates
  window.addEventListener("game:update", (e)=>{
    const payload = e.detail;
    if (payload.game !== "chess") return;
    // update board accordingly
    if (typeof applyRemoteChessState === "function") applyRemoteChessState(payload.state);
    else console.log("chess update", payload);
  });

  // Optionally react to game:started
  socket.on("game:started", (d) => {
    if (d.game === "chess" && d.conv_id == conv_id) {
      console.log("Chess started in this conv");
    }
  });
}

function init_chess(){
  console.log("init_chess called");

  // If your normal chess board renderer exists
  if (typeof renderChessBoard === "function"){
    renderChessBoard();
  }

  // Listen for local moves from your board engine
  window.addEventListener("chess:localmove", (e)=>{
    socket.emit("game:move", {
      conv_id,
      game: "chess",
      state: e.detail   // e.g. {from:"e2",to:"e4",fen:"...",san:"e4"}
    });
  });

  // Receive remote updates
  window.addEventListener("game:update", (e)=>{
    if (e.detail.game !== "chess") return;
    if (typeof applyRemoteChessState === "function"){
      applyRemoteChessState(e.detail.state);
    }
  });
}
