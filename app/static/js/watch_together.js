const watchSocket = io();
const player = document.getElementById("watchPlayer");

function loadVideo() {
    let url = document.getElementById("videoUrl").value;
    player.src = url;

    watchSocket.emit("watch:seek", {
        conv_id,
        timestamp: 0
    });
}

player.onplay = () => {
    watchSocket.emit("watch:play", { conv_id });
};

player.onpause = () => {
    watchSocket.emit("watch:pause", { conv_id });
};

player.onseeked = () => {
    watchSocket.emit("watch:seek", {
        conv_id,
        timestamp: player.currentTime
    });
};

watchSocket.on("watch:play", () => player.play());
watchSocket.on("watch:pause", () => player.pause());
watchSocket.on("watch:seek", (data) => {
    player.currentTime = data.timestamp;
});

function init_watch(){
  console.log("init_watch init");
  const video = document.getElementById("watchVideo") || document.querySelector(".watch-video");
  if (!video) return;

  // local actions -> emit
  video.addEventListener("play", ()=> socket.emit("watch:play", {conv_id}));
  video.addEventListener("pause", ()=> socket.emit("watch:pause", {conv_id}));
  video.addEventListener("seeked", ()=> socket.emit("watch:seek", {conv_id, timestamp: video.currentTime}));

  // remote actions -> perform
  window.addEventListener("watch:play", ()=> video.play());
  window.addEventListener("watch:pause", ()=> video.pause());
  window.addEventListener("watch:seek", (e)=> { video.currentTime = e.detail.timestamp; });

  // If server will broadcast a URL, listen for private:module:start with url
  socket.on("private:module:started", (d) => {
    if (d.module === "watch" && d.url) {
      video.src = d.url;
      video.play();
    }
  });
}
