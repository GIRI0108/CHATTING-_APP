const musicSocket = io();
const musicPlayer = document.getElementById("musicPlayer");

function loadTrack() {
    let url = document.getElementById("musicUrl").value;
    musicPlayer.src = url;

    musicSocket.emit("music:seek", {
        conv_id,
        timestamp: 0
    });
}

musicPlayer.onplay = () => {
    musicSocket.emit("music:play", { conv_id });
};

musicPlayer.onpause = () => {
    musicSocket.emit("music:pause", { conv_id });
};

musicPlayer.onseeked = () => {
    musicSocket.emit("music:seek", {
        conv_id,
        timestamp: musicPlayer.currentTime
    });
};

musicSocket.on("music:play", () => musicPlayer.play());
musicSocket.on("music:pause", () => musicPlayer.pause());
musicSocket.on("music:seek", (data) => {
    musicPlayer.currentTime = data.timestamp;
});

function init_music(){
  console.log("init_music");
  const player = document.getElementById("musicPlayer") || document.querySelector(".music-player");
  if (!player) return;

  player.addEventListener("play", ()=> socket.emit("music:play", {conv_id}));
  player.addEventListener("pause", ()=> socket.emit("music:pause", {conv_id}));
  player.addEventListener("seeked", ()=> socket.emit("music:seek", {conv_id, timestamp: player.currentTime}));

  window.addEventListener("music:play", ()=> player.play());
  window.addEventListener("music:pause", ()=> player.pause());
  window.addEventListener("music:seek", (e)=> { player.currentTime = e.detail.timestamp; });
}
