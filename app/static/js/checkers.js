let checkSocket = io();
let checkBoard = [];
let checkMyTurn = true;

function startGame(gameType) {
    if (gameType !== "checkers") return;

    fetch(`/start/checkers/${conv_id}`, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            initCheckers();
        });
}

function initCheckers() {
    const boardDiv = document.getElementById("gameBoard");
    boardDiv.innerHTML = `
        <iframe src="/static/checkers/index.html" class="checkers-frame"></iframe>
    `;
}

function init_checkers(){
  console.log("init_checkers");
  if (typeof renderCheckers === "function") renderCheckers();

  window.addEventListener("checkers:move", (e)=>{
    socket.emit("game:move", {conv_id, game:"checkers", state: e.detail});
  });

  window.addEventListener("game:update", (e)=>{
    if (e.detail.game !== "checkers") return;
    if (typeof applyCheckersUpdate === "function") applyCheckersUpdate(e.detail.state);
  });

  socket.on("game:started", d => {
    if (d.game == "checkers" && d.conv_id == conv_id) console.log("Checkers started");
  });
}

