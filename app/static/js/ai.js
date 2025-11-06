// ai.js — complete fixed version

document.addEventListener("DOMContentLoaded", () => {
  const aiModal = document.getElementById("aiModal");
  const aiSubmit = document.getElementById("aiSubmit");
  const aiInput = document.getElementById("aiInput");
  const aiTask = document.getElementById("aiTask");
  const langInput = document.getElementById("langInput");
  const aiResult = document.getElementById("aiResult");

  // If AI modal not found, skip initialization
  if (!aiModal) {
    console.warn("AI modal not found in DOM — skipping AI init");
    return;
  }

  // Define modal open/close globally
  window.openAIModal = () => {
    aiModal.style.display = "flex";
  };
  window.closeAIModal = () => {
    aiModal.style.display = "none";
  };

  // Handle AI submit
  if (aiSubmit) {
    aiSubmit.addEventListener("click", async () => {
      const text = aiInput.value.trim();
      const task = aiTask.value;
      const lang = langInput.value.trim();

      if (!text) {
        aiResult.textContent = "Please enter some text.";
        return;
      }

      aiResult.textContent = "Processing...";
      try {
        const res = await fetch("/api/ai/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, task, lang }),
        });

        const data = await res.json();
        aiResult.textContent = data.result || "No response from AI.";
      } catch (err) {
        aiResult.textContent = "Error: " + err.message;
      }
    });
  }

  // Handle Close button inside modal
  const aiClose = document.getElementById("aiClose");
  if (aiClose) {
    aiClose.addEventListener("click", () => {
      aiModal.style.display = "none";
    });
  }

  // ✅ FIX: Connect floating 🤖 button to modal
  const aiButton = document.getElementById("aiFloatingBtn");
  if (aiButton) {
    aiButton.addEventListener("click", () => {
      aiModal.style.display = "flex";
    });
  }

  // Close modal on outside click (optional)
  window.addEventListener("click", (e) => {
    if (e.target === aiModal) {
      aiModal.style.display = "none";
    }
  });
});
