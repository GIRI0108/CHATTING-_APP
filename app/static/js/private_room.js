// static/js/private_room.js
document.addEventListener("DOMContentLoaded", () => {
  const privateBtn = document.getElementById("privateRoomBtn");
  const privateModal = document.getElementById("privateRoomModal");
  const privateClose = document.getElementById("privateRoomClose");
  const options = document.getElementById("privateRoomOptions");
  const contentEl = document.getElementById("privateRoomContent");

  function openModal() {
    if (!privateModal) return;
    privateModal.style.display = "flex";
    contentEl.innerHTML = `<div style="padding:18px;text-align:center;">Select a module…</div>`;
  }
  function closeModal() {
    if (!privateModal) return;
    privateModal.style.display = "none";
    // stop media if any
    contentEl.querySelectorAll("video,audio").forEach(m => {
      try { m.pause(); m.src = ""; } catch(e){}
    });
    contentEl.innerHTML = "";
  }

  if (privateBtn) privateBtn.addEventListener("click", openModal);
  if (privateClose) privateClose.addEventListener("click", closeModal);
  window.addEventListener("click", (e) => { if (e.target === privateModal) closeModal(); });

  // Delegate module button clicks
  if (options) {
    options.addEventListener("click", async (ev) => {
      const btn = ev.target.closest("button[data-module]");
      if (!btn) return;
      const module = btn.dataset.module;
      contentEl.innerHTML = `<div style="padding:18px;text-align:center;">Loading ${module}…</div>`;

      // Try fetching server partial for the module
      try {
        const res = await fetch(`/private/module/${encodeURIComponent(module)}`);
        if (res.ok) {
          const html = await res.text();
          contentEl.innerHTML = html;
          // call module init if defined in partial or static js
          const fnName = `init_private_module_${module}`;
          if (typeof window[fnName] === "function") {
            try { window[fnName](); } catch (e) { console.warn("module init error", e); }
          }
          // also try to call generic module init exported by static js (e.g. initChess)
          if (typeof window[`init_${module}`] === "function") {
            try { window[`init_${module}`](); } catch (e) {}
          }
        } else {
          // fallback: show minimal UI and allow starting via socket
          contentEl.innerHTML = `<div style="padding:18px;text-align:center;">UI not available. <button id="start_${module}">Start ${module}</button></div>`;
          document.getElementById(`start_${module}`).addEventListener("click", () => startModuleViaSocket(module));
        }
      } catch (err) {
        console.error("Error loading module:", err);
        contentEl.innerHTML = `<div style="padding:18px;text-align:center;color:#c00;">Error loading module UI.</div>`;
      }
    });
  }

  // emit start event to server (server should broadcast to room)
  function startModuleViaSocket(moduleName, payload = {}) {
    if (typeof socket === "undefined") {
      alert("Realtime connection unavailable.");
      return;
    }
    if (!conv_id) {
      alert("Conversation not initialized yet.");
      return;
    }
    socket.emit("private:module:start", Object.assign({conv_id, module: moduleName}, payload));
  }

  // Listen for server acks
  if (typeof socket !== "undefined") {
    socket.on("private:module:started", (data) => {
      // simple UI feedback
      const msg = document.createElement("div");
      msg.style.padding = "8px";
      msg.style.background = "rgba(0,200,0,0.08)";
      msg.style.borderRadius = "6px";
      msg.style.marginBottom = "8px";
      msg.innerText = `${data.module} started`;
      contentEl.insertBefore(msg, contentEl.firstChild);
    });

    // forward game events to module UI (modules can listen to these)
    socket.on("game:update", (payload) => {
      // dispatch custom DOM event so module code can respond
      window.dispatchEvent(new CustomEvent("game:update", {detail: payload}));
    });

    socket.on("watch:play", (d) => window.dispatchEvent(new CustomEvent("watch:play", {detail:d})));
    socket.on("watch:pause", (d) => window.dispatchEvent(new CustomEvent("watch:pause", {detail:d})));
    socket.on("watch:seek", (d) => window.dispatchEvent(new CustomEvent("watch:seek", {detail:d})));
    socket.on("music:play", (d) => window.dispatchEvent(new CustomEvent("music:play", {detail:d})));
    socket.on("music:pause", (d) => window.dispatchEvent(new CustomEvent("music:pause", {detail:d})));
    socket.on("music:seek", (d) => window.dispatchEvent(new CustomEvent("music:seek", {detail:d})));
  }
});
