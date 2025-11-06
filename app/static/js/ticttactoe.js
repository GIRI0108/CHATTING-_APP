const socketTTT = io();
let tttBoard = "";
let tttMyTurn = true;
let tttGameActive = false;

function startGame(gameType) {
    if (gameType !== "tictactoe") return;

    fetch(`/start/tictactoe/${conv_id}`, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            tttBoard = data.state;
            tttGameActive = true;
            renderTicTacToe();
        });
}

function renderTicTacToe() {
    const boardDiv = document.getElementById("gameBoard");
    boardDiv.innerHTML = "";

    if (!tttGameActive) return;

    let html = '<div class="ttt-grid">';
    for (let i = 0; i < 9; i++) {
        let cell = tttBoard[i] === "-" ? "" : tttBoard[i].toUpperCase();
        html += `<div class="ttt-cell" onclick="tttMove(${i})">${cell}</div>`;
    }
    html += "</div>";

    boardDiv.innerHTML = html;
}

function tttMove(index) {
    if (!tttMyTurn || tttBoard[index] !== "-" || !tttGameActive) return;

    let arr = tttBoard.split("");
    arr[index] = "x";
    tttBoard = arr.join("");

    socketTTT.emit("game:move", {
        conv_id,
        game: "tictactoe",
        state: tttBoard
    });

    tttMyTurn = false;
    renderTicTacToe();
}

// Receive opponent move
socketTTT.on("game:update", (data) => {
    if (data.game !== "tictactoe") return;

    tttBoard = data.state;
    tttMyTurn = true;
    renderTicTacToe();
});

function init_tictactoe(){
  console.log("init_tictactoe");
  // If your tictactoe has a start button handler, ensure it emits `game:start`:
  const btn = document.getElementById("tttStart") || document.querySelector("[data-ttt-start]");
  if (btn) btn.addEventListener("click",()=> socket.emit("game:start",{conv_id, game:"tictactoe"}));

  // when local move occurs, dispatch `tictactoe:move` custom event with state
  window.addEventListener("tictactoe:localmove", (e)=> {
    socket.emit("game:move", {conv_id, game:"tictactoe", state: e.detail});
  });

  window.addEventListener("game:update", (e)=>{
    if (e.detail.game !== "tictactoe") return;
    if (typeof applyTicTacToeUpdate === "function") applyTicTacToeUpdate(e.detail.state);
  });
}
